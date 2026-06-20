import asyncio
from dataclasses import dataclass
from enum import Enum
import platform
import socket
import subprocess

from data.regions import LATENCY_THRESHOLDS, REGIONS

# ======================
# Platform Configuration
# ======================

SYSTEM = platform.system()

# ======================
# Enums
# ======================


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


# ======================
# Models
# ======================


@dataclass
class PingResult:
    region_code: str
    hostname: str
    ip: str | None

    succeeded_count: int = 0
    failed_count: int = 0

    last_ping_status: PingStatus = PingStatus.INITIALIZING
    last_ping_latency: float | None = None
    packet_loss_percentage: float = 0.0

    def update(self, status: PingStatus, latency: float | None):
        if status == PingStatus.SUCCEEDED:
            self.succeeded_count += 1
        elif status == PingStatus.FAILED:
            self.failed_count += 1

        total = self.succeeded_count + self.failed_count
        self.packet_loss_percentage = (
            (self.failed_count / total) * 100 if total > 0 else 0
        )

        self.last_ping_status = status
        self.last_ping_latency = latency


# ======================
# Helpers
# ======================


def classify_latency(latency):
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
    except Exception:
        pass
    return None


async def resolve_hostname(hostname):
    loop = asyncio.get_running_loop()
    try:
        addrinfo = await loop.getaddrinfo(hostname, None)
        return addrinfo[0][4][0] if addrinfo else None
    except socket.gaierror:
        return None


# ======================
# Ping Execution
# ======================


async def run_ping_once(ip):
    cmd = ["ping", "-n", "1", ip] if SYSTEM == "Windows" else ["ping", "-c", "1", ip]

    proc = None

    try:
        kwargs = {}

        if SYSTEM == "Windows":
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

        async for line_bytes in proc.stdout:
            line = line_bytes.decode("utf-8", errors="ignore").strip().lower()

            latency = parse_latency(line)
            if latency is not None:
                return PingStatus.SUCCEEDED, latency

            if "timed out" in line or "unreachable" in line:
                return PingStatus.FAILED, None

        return PingStatus.FAILED, None

    except Exception:
        return PingStatus.ERROR, None

    finally:
        if proc:
            try:
                if proc.returncode is None:
                    proc.kill()
                await proc.wait()
            except Exception:
                pass


# ======================
# Continuous Ping Loop
# ======================


async def ping_loop(result, interval):
    try:
        while True:
            if result.ip is None:
                new_ip = await resolve_hostname(result.hostname)

                if new_ip is not None:
                    result.ip = new_ip
                    result.last_ping_status = PingStatus.INITIALIZING
                else:
                    result.last_ping_status = PingStatus.UNRESOLVED
                    await asyncio.sleep(interval)
                    continue

            try:
                status, latency = await asyncio.wait_for(
                    run_ping_once(result.ip), timeout=3
                )
            except asyncio.TimeoutError:
                status, latency = PingStatus.FAILED, None

            result.update(status, latency)

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        raise


# ======================
# Orchestration
# ======================


async def ping_all_regions_continuous(interval=5):
    results = {}
    tasks = []

    for region_code, region_data in REGIONS.items():
        hostname = region_data.get("service_endpoint")

        ip = await resolve_hostname(hostname)

        status = PingStatus.INITIALIZING if ip else PingStatus.UNRESOLVED

        result = PingResult(
            region_code=region_code,
            hostname=hostname,
            ip=ip,
            last_ping_status=status,
            packet_loss_percentage=100.0 if ip is None else 0.0,
        )

        results[region_code] = result

        tasks.append(asyncio.create_task(ping_loop(result, interval)))

    return results, tasks
