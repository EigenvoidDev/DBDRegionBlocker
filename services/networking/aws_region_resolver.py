import ipaddress
import json
import os
from pathlib import Path
import platform

import requests

AWS_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"

# ======================
# Platform Configuration
# ======================

SYSTEM = platform.system()

# ======================
# App Configuration
# ======================

APP_NAME = "DBDRegionBlocker"

# ======================
# Cache Path
# ======================


def get_cache_path():
    if SYSTEM == "Windows":
        appdata = os.getenv("APPDATA")
        if not appdata:
            appdata = str(Path.home() / "AppData" / "Roaming")

        base = Path(appdata) / APP_NAME / "cache"

    elif SYSTEM == "Darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME / "cache"

    else:
        base = (
            Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config")))
            / APP_NAME
            / "cache"
        )

    base.mkdir(parents=True, exist_ok=True)
    return base / "aws_ip_ranges.json"


# ======================
# AWS Region Resolver
# ======================


class AWSRegionResolver:
    def __init__(self, use_cache=True):
        self.use_cache = use_cache
        self.cidr_index = []
        self.cache_file = get_cache_path()

    # ----------------- Public API -----------------
    def load(self):
        region_map = self._fetch_aws_ranges()
        self.cidr_index = self._build_networks(region_map)

    def get_region(self, ip):
        try:
            ip_addr = ipaddress.ip_address(ip)
        except ValueError:
            return None

        for network, region in self.cidr_index:
            if ip_addr in network:
                return region

        return None

    # ----------------- Data Fetching -----------------
    def _fetch_aws_ranges(self):
        cache_file = self.cache_file

        cached = None

        if self.use_cache and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
            except Exception:
                cache_file.unlink(missing_ok=True)
                cached = None

        try:
            response = requests.get(AWS_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception:
            if cached:
                return cached["data"]
            return {}

        remote_date = data.get("createDate")

        if cached and cached.get("createDate") == remote_date and "data" in cached:
            return cached["data"]

        regions = {}

        for prefix in data["prefixes"]:
            region = prefix["region"]
            cidr = prefix["ip_prefix"]

            if region not in regions:
                regions[region] = []

            regions[region].append(cidr)

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"createDate": remote_date, "data": regions}, f, indent=2)
        except Exception:
            pass

        return regions

    # ----------------- Network Compilation -----------------
    def _build_networks(self, region_map):
        compiled = []

        for region, cidrs in region_map.items():
            for cidr in cidrs:
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                    compiled.append((network, region))
                except ValueError:
                    continue

        return compiled
