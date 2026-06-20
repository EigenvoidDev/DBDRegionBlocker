from enum import Enum
import json
import os
from pathlib import Path
import platform
import subprocess

from data.regions import REGIONS

# ========================
# Platform Configuration
# ========================

SYSTEM = platform.system()


def get_hosts_path():
    try:
        return HOSTS_PATHS[SYSTEM]
    except KeyError:
        raise RuntimeError(f"Unsupported platform: {SYSTEM}")


# ========================
# App Configuration
# ========================

APP_NAME = "DBDRegionBlocker"

# ========================
# Config Path
# ========================


def get_config_path():
    if SYSTEM == "Windows":
        appdata = os.getenv("APPDATA")
        if not appdata:
            appdata = str(Path.home() / "AppData" / "Roaming")

        base = Path(appdata) / APP_NAME

    elif SYSTEM == "Darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME

    else:
        base = (
            Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / APP_NAME
        )

    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"


# ========================
# Config System
# ========================


def create_default_config():
    return {
        "regions": {code: False for code in REGIONS.keys()},
        "packet_sniffer_enabled": True,
    }


def load_config():
    config_path = get_config_path()

    if not config_path.exists():
        config = create_default_config()
        save_config(config)
        return config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        changed = False

        if "regions" not in config:
            config["regions"] = {code: False for code in REGIONS.keys()}
            changed = True

        if "packet_sniffer_enabled" not in config:
            config["packet_sniffer_enabled"] = True
            changed = True

        if changed:
            save_config(config)

        return config

    except (OSError, json.JSONDecodeError):
        config = create_default_config()
        save_config(config)
        return config


def save_config(config):
    config_path = get_config_path()

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# ========================
# Constants
# ========================

HOSTS_SECTION_START = "# BEGIN DBD REGION BLOCKER SECTION"
HOSTS_SECTION_END = "# END DBD REGION BLOCKER SECTION"

HOSTS_PATHS = {
    "Windows": Path(r"C:\Windows\System32\drivers\etc\hosts"),
    "Linux": Path("/etc/hosts"),
    "Darwin": Path("/etc/hosts"),
}

FLUSH_COMMANDS = {
    "Windows": [["ipconfig", "/flushdns"]],
    "Linux": [["resolvectl", "flush-caches"]],
    "Darwin": [
        ["dscacheutil", "-flushcache"],
        ["killall", "-HUP", "mDNSResponder"],
    ],
}

# ========================
# Region Mapping
# ========================

ENDPOINT_TO_REGION_CODE = {
    data["udp_ping_beacon_endpoint"]: code for code, data in REGIONS.items()
}

# ========================
# Status Enums
# ========================


class HostsUpdateStatus(Enum):
    SUCCESS = 1
    NO_CHANGES = 2
    PERMISSION_ERROR = 3
    WRITE_ERROR = 4


class HostsReadStatus(Enum):
    OK = 1
    PERMISSION_ERROR = 2
    READ_ERROR = 3


# ========================
# Hosts Section Management
# ========================


def strip_existing_section(lines):
    new_lines = []
    in_block = False

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


def build_hosts_section_lines(config):
    lines = [
        HOSTS_SECTION_START,
        "# Managed by DBD Region Blocker",
        "# Maps region endpoints to 0.0.0.0 to block access",
        "# Do not edit this section manually",
        "",
    ]

    regions = config["regions"]

    for region_code, region_data in REGIONS.items():
        hostname = region_data["udp_ping_beacon_endpoint"]
        is_blocked = regions.get(region_code, False)

        prefix = "0.0.0.0 " if is_blocked else "# 0.0.0.0 "
        lines.append(prefix + hostname)

    lines += ["", HOSTS_SECTION_END]

    return lines


# ========================
# Hosts File Operations
# ========================


def write_hosts_file(lines):
    try:
        with open(get_hosts_path(), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return HostsUpdateStatus.SUCCESS

    except PermissionError:
        return HostsUpdateStatus.PERMISSION_ERROR

    except OSError:
        return HostsUpdateStatus.WRITE_ERROR


# ========================
# DNS Cache Control
# ========================


def flush_dns_cache():
    commands = FLUSH_COMMANDS.get(SYSTEM)

    if not commands:
        return

    for cmd in commands:
        try:
            subprocess.run(cmd, check=True)
        except Exception:
            pass


# ========================
# Core Sync Logic
# ========================


def apply_config_to_hosts():
    config = load_config()
    path = get_hosts_path()

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except PermissionError:
        return HostsUpdateStatus.PERMISSION_ERROR

    new_section = build_hosts_section_lines(config)
    stripped = strip_existing_section(lines)

    result = write_hosts_file(stripped + new_section)

    if result == HostsUpdateStatus.SUCCESS:
        flush_dns_cache()

    return result


def initialize_hosts_file():
    config = load_config()
    path = get_hosts_path()

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except PermissionError:
        return HostsUpdateStatus.PERMISSION_ERROR

    if HOSTS_SECTION_START in content and HOSTS_SECTION_END in content:
        return apply_config_to_hosts()

    lines = content.strip().splitlines()
    lines.extend(build_hosts_section_lines(config))

    result = write_hosts_file(lines)

    if result == HostsUpdateStatus.SUCCESS:
        flush_dns_cache()

    return result


# ========================
# Region Control
# ========================


def set_region_block(region_code, is_blocked):
    config = load_config()
    config["regions"][region_code] = is_blocked
    save_config(config)


# ========================
# Packet Sniffer Settings
# ========================


def get_packet_sniffer_enabled():
    config = load_config()
    return config.get("packet_sniffer_enabled", True)


def set_packet_sniffer_enabled(enabled):
    config = load_config()
    config["packet_sniffer_enabled"] = enabled
    save_config(config)


# ========================
# State Queries
# ========================


def get_blocked_regions_from_hosts():
    blocked_region_codes = []
    path = get_hosts_path()

    try:
        with open(path, "r", encoding="utf-8") as f:
            in_block = False

            for line in f:
                stripped = line.strip()

                if stripped == HOSTS_SECTION_START:
                    in_block = True
                    continue

                if stripped == HOSTS_SECTION_END:
                    break

                if in_block and not stripped.startswith("#"):
                    parts = stripped.split()

                    if len(parts) >= 2:
                        hostname = parts[1]
                        region_code = ENDPOINT_TO_REGION_CODE.get(hostname)

                        if region_code:
                            blocked_region_codes.append(region_code)

        return HostsReadStatus.OK, blocked_region_codes

    except PermissionError:
        return HostsReadStatus.PERMISSION_ERROR, blocked_region_codes

    except OSError:
        return HostsReadStatus.READ_ERROR, blocked_region_codes


# ========================
# Exit Cleanup
# ========================


def reset_hosts_on_exit():
    path = get_hosts_path()

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    except PermissionError:
        return HostsUpdateStatus.PERMISSION_ERROR

    config = load_config()

    temp_config = {"regions": {code: False for code in config["regions"]}}

    stripped = strip_existing_section(lines)
    new_section = build_hosts_section_lines(temp_config)

    result = write_hosts_file(stripped + new_section)

    if result == HostsUpdateStatus.SUCCESS:
        flush_dns_cache()

    return result
