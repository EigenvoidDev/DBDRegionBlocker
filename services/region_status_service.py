import time

import requests

API_URL = "https://api2.deadbyqueue.com/regions"


class RegionStatusService:
    def __init__(self, timeout=5, cache_ttl=10):
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache = None
        self._last_fetch = 0

    def _is_cache_valid(self):
        return (
            self._cache is not None
            and (time.time() - self._last_fetch) < self.cache_ttl
        )

    def fetch_status(self):
        if self._is_cache_valid():
            return self._cache

        try:
            response = requests.get(API_URL, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, dict):
                return self._cache or {}

            regions = data.get("regions", {})

            self._cache = regions
            self._last_fetch = time.time()

            return regions

        except (requests.RequestException, ValueError):
            return self._cache or {}

    def get_split(self):
        data = self.fetch_status()

        online = {region: status for region, status in data.items() if status is True}

        offline = {region: status for region, status in data.items() if status is False}

        return online, offline