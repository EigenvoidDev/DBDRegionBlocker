from collections import deque
import time


class SessionTracker:
    def __init__(self, window=2.0, threshold=10):
        self.window = window
        self.threshold = threshold

        self.ip_hits = {}
        self.current_server = None

    def observe(self, ip):
        now = time.time()

        if ip not in self.ip_hits:
            self.ip_hits[ip] = deque()

        timestamps = self.ip_hits[ip]
        timestamps.append(now)

        while timestamps and now - timestamps[0] > self.window:
            timestamps.popleft()

    def get_best(self):
        best_ip = None
        best_rate = 0

        for ip, timestamps in self.ip_hits.items():
            rate = len(timestamps)
            if rate > best_rate:
                best_rate = rate
                best_ip = ip

        return best_ip, best_rate

    def update(self):
        ip, rate = self.get_best()

        if ip and rate >= self.threshold:
            if ip != self.current_server:
                self.current_server = ip
                return ip

        return None

    def reset(self):
        self.ip_hits.clear()
        self.current_server = None