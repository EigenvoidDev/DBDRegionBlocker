import platform
import subprocess
from pathlib import Path

from config import REGIONS

# =====================
# Constants
# =====================
SECTION_START = "# DBDRegionSelectorHostsSectionStart"
SECTION_END = "# DBDRegionSelectorHostsSectionEnd"
ERROR_MESSAGE = "Administrator privileges required. Please run this application as an administrator."

HOSTS_PATH = {
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


class UnsupportedPlatformError(Exception):
    pass


# =====================
# Helpers
# =====================
def get_hosts_path():
    system = platform.system()
    try:
        return HOSTS_PATH[system]
    except KeyError:
        raise UnsupportedPlatformError(f"Unsupported platform: {system}")


def strip_existing_section(lines):
    new_lines, in_block = [], False
    for line in lines:
        stripped = line.strip()
        if stripped == SECTION_START:
            in_block = True
            continue
        if stripped == SECTION_END:
            in_block = False
            continue
        if not in_block:
            new_lines.append(line.rstrip("\n"))
    return new_lines


def build_hosts_section_lines(active_region=None, comment_all=False):
    lines = [
        SECTION_START,
        "# This section is managed by DBD Region Selector.",
        "# It maps endpoints to 0.0.0.0 to block access to specific regions.",
        "# Do not edit this section manually.",
        "",
    ]
    for region_name, region_data in REGIONS.items():
        hostname = region_data["udp_ping_beacon_endpoint"]
        if comment_all or region_name == active_region:
            lines.append(f"# 0.0.0.0 {hostname}")
        else:
            lines.append(f"0.0.0.0 {hostname}")
    lines.append("")
    lines.append(SECTION_END)
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
        print(ERROR_MESSAGE)
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
        print(ERROR_MESSAGE)
        return False

    if SECTION_START in content and SECTION_END in content:
        return True

    lines = content.strip().splitlines()
    lines.extend(build_hosts_section_lines(comment_all=True))

    if write_hosts_file(lines):
        flush_dns_cache()
        return True
    else:
        return False


def get_active_regions_from_hosts():
    active_regions = []

    try:
        with open(get_hosts_path(), "r", encoding="utf-8") as f:
            in_block = False
            for line in f:
                stripped = line.strip()
                if stripped == SECTION_START:
                    in_block = True
                    continue
                elif stripped == SECTION_END:
                    break
                if in_block and stripped.startswith("# 0.0.0.0"):
                    for region_name, region_data in REGIONS.items():
                        if region_data["udp_ping_beacon_endpoint"] in stripped:
                            active_regions.append(region_name)
                            break
    except PermissionError:
        print(ERROR_MESSAGE)
        raise

    return active_regions


def update_hosts_file(active_region=None, comment_all=False):
    try:
        with open(get_hosts_path(), "r", encoding="utf-8") as f:
            lines = f.readlines()
    except PermissionError:
        return "error"

    new_lines = strip_existing_section(lines)
    hosts_section = build_hosts_section_lines(active_region, comment_all)

    # Compare with existing section
    normalized_new = [line.rstrip("\n") for line in hosts_section]
    normalized_existing = (
        [line.rstrip("\n") for line in lines[-len(normalized_new) :]]
        if len(lines) >= len(normalized_new)
        else []
    )

    if normalized_existing == normalized_new:
        return "already_set"

    if write_hosts_file(new_lines + hosts_section):
        flush_dns_cache()
        return "updated"

    return "error"