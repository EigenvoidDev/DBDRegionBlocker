import platform
import socket
import subprocess
import threading

from config import REGIONS, LATENCY_THRESHOLDS

# ===============
# Global State
# ===============
lock = threading.Lock()
ping_processes = {}
threads = {}
results = {}

# ===============
# Helpers
# ===============
def resolve_hostname(hostname):
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror as e:
        print(f"Failed to resolve {hostname}: {e}")
        return None


def classify_latency(latency, error=None):
    if latency is None:
        return error or "no_response"
    if latency <= LATENCY_THRESHOLDS["good"]:
        return "good"
    if latency <= LATENCY_THRESHOLDS["ok"]:
        return "ok"
    return "bad"


def parse_latency(line):
    try:
        if "time=" in line:
            time_str = line.split("time=")[1].split()[0].replace("ms", "").strip()
            return float(time_str)
        if "Average =" in line:
            return float(line.split("Average =")[-1].strip().replace("ms", ""))
    except Exception as e:
        print(f"Latency parse error: {e} (line: {line})")
    return None


def is_ping_reply(line):
    return any(token in line for token in ("time=", "TTL=", "ttl="))


def build_result_entry(region_data, ip, status):
    return {
        "region": region_data["region"],
        "hostname": region_data["service_endpoint"],
        "ip": ip,
        "latency_ms": None,
        "packet_loss_percentage": None if ip else 100.0,
        "status": status,
    }


# ===============
# Ping Management
# ===============
def start_continuous_ping(host, result_dict, region_name):
    system = platform.system()
    cmd = ["ping", "-t", host] if system == "Windows" else ["ping", host]
    creationflags = subprocess.CREATE_NO_WINDOW if system == "Windows" else 0

    def run():
        sent, received = 0, 0
        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=creationflags,
            ) as proc:
                ping_processes[region_name] = proc
                for line in proc.stdout:
                    if region_name not in result_dict:
                        break
                    latency = parse_latency(line)
                    if is_ping_reply(line):
                        sent += 1
                    if latency is not None:
                        received += 1
                        with lock:
                            result_dict[region_name].update(
                                {
                                    "latency_ms": latency,
                                    "status": classify_latency(latency),
                                }
                            )
                    if sent > 0:
                        packet_loss = ((sent - received) / sent) * 100
                        with lock:
                            result_dict[region_name].update(
                                {
                                    "packet_loss_percentage": round(packet_loss, 2),
                                    "packet_loss_str": f"{packet_loss:.2f}%",
                                }
                            )
        except Exception as e:
            print(f"[{region_name}] Continuous ping error: {e}")
            with lock:
                result_dict[region_name]["status"] = "error"

    thread = threading.Thread(target=run, daemon=True)
    threads[region_name] = thread
    thread.start()
    return thread


def ping_all_regions():
    for region_name, region_data in REGIONS.items():
        hostname = region_data["service_endpoint"]
        ip = resolve_hostname(hostname)
        status = "initializing" if ip else "unresolved"
        results[region_name] = build_result_entry(region_data, ip, status)
        if ip:
            start_continuous_ping(ip, results, region_name)
    return results


def terminate_all_pings():
    for region, proc in ping_processes.items():
        try:
            if proc.poll() is None:
                proc.terminate()
        except Exception as e:
            print(f"Error terminating ping for {region}: {e}")
    ping_processes.clear()
    threads.clear()