from enum import Enum
from pathlib import Path
import platform
import subprocess

from config import REGIONS

# =====================
# Constants
# =====================
HOSTS_SECTION_START = "# BEGIN DBD Region Selector Section"
HOSTS_SECTION_END = "# END DBD Region Selector Section"
ADMIN_PRIVILEGES_ERROR = "This action requires administrator privileges. Please restart the program as an administrator."

HOSTS_PATHS = {
    "Windows": Path(r"C:\Windows\System32\drivers\etc\hosts"),
    "Linux": Path("/etc/hosts"),
    "Darwin": Path("/etc/hosts"),  # macOS
}

FLUSH_COMMANDS = {
    "Windows": [["ipconfig", "/flushdns"]],
    "Linux": [["sudo", "systemd-resolve", "--flush-caches"]],
    "Darwin": [
        ["sudo", "dscacheutil", "-flushcache"],
        ["sudo", "killall", "-HUP", "mDNSResponder"],
    ],
}

# Precomputed mapping of UDP endpoints → region names
ENDPOINT_TO_REGION = {
    data["udp_ping_beacon_endpoint"]: name for name, data in REGIONS.items()
}

# =====================
# Enums
# =====================
class HostsUpdateStatus(Enum):
    UPDATE_SUCCESS = 1
    ALREADY_UP_TO_DATE = 2
    PERMISSION_ERROR = 3
    WRITE_ERROR = 4


# =====================
# Helpers
# =====================
def get_hosts_path():
    system = platform.system()
    try:
        return HOSTS_PATHS[system]
    except KeyError:
        raise RuntimeError(f"Unsupported platform: {system}")


def strip_existing_section(lines):
    new_lines, in_block = [], False
    for line in lines:
        stripped = line.strip()
        if stripped == HOSTS_SECTION_START:
            in_block = True
            continue
        if stripped == HOSTS_SECTION_END:
            in_block = False
            continue
        if not in_block:
            new_lines.append(line.rstrip("\n"))
    return new_lines


def build_hosts_section_lines(active_regions=None, all_regions_active=False):
    if active_regions is None:
        active_regions = []

    lines = [
        HOSTS_SECTION_START,
        "# This section is managed by DBD Region Selector.",
        "# It maps endpoints to 0.0.0.0 to block access to specific regions.",
        "# Do not edit this section manually.",
        "",
    ]

    for region_name, region_data in REGIONS.items():
        hostname = region_data["udp_ping_beacon_endpoint"]
        if all_regions_active or region_name in active_regions:
            lines.append(f"# 0.0.0.0 {hostname}")
        else:
            lines.append(f"0.0.0.0 {hostname}")

    lines.append("")
    lines.append(HOSTS_SECTION_END)
    return lines


# =====================
# Hosts File Operations
# =====================
def write_hosts_file(lines):
    try:
        with open(get_hosts_path(), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except PermissionError:
        print(ADMIN_PRIVILEGES_ERROR)
        return False


def flush_dns_cache():
    system = platform.system()
    commands = FLUSH_COMMANDS.get(system)
    if not commands:
        print(f"Unsupported platform: {system}")
        return

    for cmd in commands:
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"Failed to run {cmd}: {e}")


def initialize_hosts_file():
    try:
        with open(get_hosts_path(), "r", encoding="utf-8") as f:
            content = f.read()
    except PermissionError:
        print(ADMIN_PRIVILEGES_ERROR)
        return False

    if HOSTS_SECTION_START in content and HOSTS_SECTION_END in content:
        return True

    lines = content.strip().splitlines()
    lines.extend(build_hosts_section_lines(all_regions_active=True))

    if write_hosts_file(lines):
        flush_dns_cache()
        return True
    else:
        return False


def update_hosts_file(active_regions=None, all_regions_active=False):
    try:
        with open(get_hosts_path(), "r", encoding="utf-8") as f:
            lines = f.readlines()
    except PermissionError:
        print(ADMIN_PRIVILEGES_ERROR)
        return HostsUpdateStatus.PERMISSION_ERROR

    new_lines = strip_existing_section(lines)
    hosts_section = build_hosts_section_lines(active_regions, all_regions_active)

    # Compare with existing section
    normalized_new = [line.rstrip("\n") for line in hosts_section]
    normalized_existing = (
        [line.rstrip("\n") for line in lines[-len(normalized_new) :]]
        if len(lines) >= len(normalized_new)
        else []
    )

    if normalized_existing == normalized_new:
        return HostsUpdateStatus.ALREADY_UP_TO_DATE

    if write_hosts_file(new_lines + hosts_section):
        flush_dns_cache()
        return HostsUpdateStatus.UPDATE_SUCCESS

    return HostsUpdateStatus.WRITE_ERROR


def get_active_regions_from_hosts():
    active_regions = []

    try:
        with open(get_hosts_path(), "r", encoding="utf-8") as f:
            in_block = False
            for line in f:
                stripped = line.strip()
                if stripped == HOSTS_SECTION_START:
                    in_block = True
                    continue
                elif stripped == HOSTS_SECTION_END:
                    break
                if in_block and stripped.startswith("# 0.0.0.0"):
                    parts = stripped.split()
                    if len(parts) >= 2:
                        hostname = parts[1]
                        region_name = ENDPOINT_TO_REGION.get(hostname)
                        if region_name:
                            active_regions.append(region_name)

    except PermissionError:
        print(ADMIN_PRIVILEGES_ERROR)
        raise

    return active_regions