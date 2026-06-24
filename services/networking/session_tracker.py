from collections import deque
import time


class SessionTracker:
    def __init__(self, window=3.0, min_hits_threshold=15):
        self.window = window
        self.min_hits_threshold = min_hits_threshold

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
        best_hit_count = 0

        for ip, timestamps in self.ip_hits.items():
            hit_count = len(timestamps)
            if hit_count > best_hit_count:
                best_hit_count = hit_count
                best_ip = ip

        return best_ip, best_hit_count

    def evaluate_current_server(self):
        ip, hit_count = self.get_best()

        if ip and hit_count >= self.min_hits_threshold:
            if ip != self.current_server:
                self.current_server = ip
                return ip

        return None

    def reset(self):
        self.ip_hits.clear()
        self.current_server = None
