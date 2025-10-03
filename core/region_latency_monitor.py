import asyncio
from enum import Enum
import platform
import socket
import subprocess

from config import LATENCY_THRESHOLDS, REGIONS

# =============
# Enums
# =============
class PingStatus(Enum):
    INITIALIZING = "Initializing"
    UNRESOLVED = "Unresolved"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    ERROR = "Error"


class LatencyQuality(Enum):
    NO_RESPONSE = 0
    GOOD = 1
    OK = 2
    BAD = 3


# =============
# Helpers
# =============
def classify_latency(latency, error=None):
    if latency is None:
        return LatencyQuality.NO_RESPONSE
    if latency <= LATENCY_THRESHOLDS["good"]:
        return LatencyQuality.GOOD
    if latency <= LATENCY_THRESHOLDS["ok"]:
        return LatencyQuality.OK
    return LatencyQuality.BAD


def parse_latency(line):
    try:
        if "time=" in line:
            return float(line.split("time=")[1].split()[0].replace("ms", "").strip())
    except Exception as e:
        print(f"Latency parse error: {e} (line: {line})")
    return None


async def resolve_hostname(hostname):
    loop = asyncio.get_running_loop()
    try:
        return await loop.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        print(f"Failed to resolve {hostname}: {e}")
        return None


def build_initial_result(region_name, region_data, ip, status):
    return {
        "region_name": region_name,
        "region_code": region_data["region"],
        "hostname": region_data["service_endpoint"],
        "ip": ip,
        "succeeded_count": 0,
        "failed_count": 0,
        "last_ping_status": status,
        "last_ping_latency": None,
        "packet_loss_percentage": 100.0 if ip is None else 0.0,
    }


# =============
# Async Ping
# =============
async def async_ping(region_name, ip, results, interval=5):
    system = platform.system()
    cmd = ["ping", "-n", "1", ip] if system == "Windows" else ["ping", "-c", "1", ip]

    succeeded, failed = 0, 0
    proc = None

    try:
        while True:
            kwargs = {}
            if system == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs["startupinfo"] = startupinfo
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                **kwargs,
            )

            latency = None
            status = PingStatus.INITIALIZING

            async for line_bytes in proc.stdout:
                line = line_bytes.decode("utf-8", errors="ignore").strip()
                line_lower = line.lower()

                latency = parse_latency(line)
                if latency is not None:
                    succeeded += 1
                    status = PingStatus.SUCCEEDED
                    break
                elif (
                    "request timed out" in line_lower
                    or "destination host unreachable" in line_lower
                ):
                    failed += 1
                    status = PingStatus.FAILED
                    break

            total = succeeded + failed
            packet_loss_percentage = (failed / total) * 100 if total > 0 else 0

            results[region_name].update(
                {
                    "succeeded_count": succeeded,
                    "failed_count": failed,
                    "last_ping_status": status,
                    "last_ping_latency": latency,
                    "packet_loss_percentage": round(packet_loss_percentage, 2),
                }
            )

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        if proc and proc.returncode is None:
            proc.terminate()
            await proc.wait()
        raise

    except Exception as e:
        results[region_name].update(
            {"last_ping_status": PingStatus.ERROR, "last_ping_latency": None}
        )
        print(f"[{region_name}] Ping error: {e}")


# =============
# Runner
# =============
async def ping_all_regions_continuous(results, interval=5):
    tasks = []

    for region_name, region_data in REGIONS.items():
        hostname = region_data.get("service_endpoint")
        ip = None

        addrinfo = await resolve_hostname(hostname)
        if addrinfo:
            ip = addrinfo[0][4][0]  # First resolved IP (IPv4 or IPv6)

        status = PingStatus.INITIALIZING if ip else PingStatus.UNRESOLVED
        results[region_name] = build_initial_result(
            region_name, region_data, ip, status
        )

        if ip:
            task = asyncio.create_task(async_ping(region_name, ip, results, interval))
            tasks.append(task)

    return tasks