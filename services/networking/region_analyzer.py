import ipaddress
import queue
import threading
import time

import psutil

from .aws_region_resolver import AWSRegionResolver
from .packet_sniffer import PacketSniffer
from .session_tracker import SessionTracker


class AnalyzerState:
    def __init__(self, is_game_running, server_ip, region_code):
        self.is_game_running = is_game_running
        self.server_ip = server_ip
        self.region_code = region_code


class RegionAnalyzer:
    def __init__(self):
        self.resolver = AWSRegionResolver()
        self.tracker = SessionTracker()

        self.packet_queue = queue.Queue(maxsize=10000)

        self.game_active = False
        self.current_server_ip = None
        self.current_region = None

        self.on_server_detected = None

        self._running = False
        self._sniffer_thread = None
        self._sniffer = None

        self._last_game_check = 0
        self._game_check_interval = 1.0

        self._sniffer_supported = PacketSniffer.supported

    # ----------------- Lifecycle -----------------
    def stop(self):
        self._running = False

        if self._sniffer and self._sniffer.handle is not None:
            try:
                self._sniffer.handle.close()
            except Exception:
                pass

        if self._sniffer_thread and self._sniffer_thread.is_alive():
            self._sniffer_thread.join(timeout=2)

        self._sniffer_thread = None
        self._sniffer = None

    # ----------------- Game Detection -----------------
    def is_game_running(self):
        now = time.monotonic()

        if now - self._last_game_check < self._game_check_interval:
            return self.game_active

        self._last_game_check = now

        running = False

        for proc in psutil.process_iter(["name"]):
            try:
                if "DeadByDaylight" in (proc.info["name"] or ""):
                    running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self.game_active = running
        return running

    # ----------------- Sniffer Thread -----------------
    def _sniffer_worker(self):
        print("[PacketSniffer] Started")

        if not self._sniffer_supported:
            return

        try:
            with PacketSniffer() as sniffer:
                self._sniffer = sniffer

                try:
                    for packet in sniffer:
                        if not self._running:
                            break

                        try:
                            sniffer.send(packet)

                            if packet.is_outbound and packet.udp:
                                ip = packet.dst_addr

                                try:
                                    self.packet_queue.put_nowait(ip)
                                except queue.Full:
                                    try:
                                        self.packet_queue.get_nowait()
                                    except queue.Empty:
                                        pass

                                    try:
                                        self.packet_queue.put_nowait(ip)
                                    except queue.Full:
                                        pass

                        except Exception as e:
                            print(f"[PacketSniffer] Packet Error: {e}")

                except (OSError, RuntimeError) as e:
                    if getattr(e, "winerror", None) != 995:
                        print(f"[PacketSniffer] Capture Error: {e}")

        finally:
            print("[PacketSniffer] Stopped")
            self._sniffer = None

    # ----------------- Main Runtime Loop -----------------
    def run(self):
        if self._running:
            print("[RegionAnalyzer] Already running")
            return

        print("[RegionAnalyzer] Started")

        self._running = True

        self.resolver.load()

        if self._sniffer_supported:
            self._sniffer_thread = threading.Thread(target=self._sniffer_worker)
            self._sniffer_thread.start()

        try:
            while self._running:

                try:
                    ip = self.packet_queue.get(timeout=0.5)
                except queue.Empty:
                    ip = None

                try:
                    # ----------------- Game State -----------------
                    previous = self.game_active
                    running = self.is_game_running()

                    if running != previous:
                        self.tracker.reset()

                        if not running:
                            self.current_server_ip = None
                            self.current_region = None

                            if callable(self.on_server_detected):
                                self.on_server_detected("", "")

                    if not running:
                        continue

                    if ip is None:
                        continue

                    # ----------------- IP Validation -----------------
                    try:
                        if ipaddress.ip_address(ip).version != 4:
                            continue
                    except ValueError:
                        continue

                    # ----------------- Region Filtering -----------------
                    packet_region = self.resolver.get_region(ip)

                    if not packet_region:
                        continue

                    # ----------------- Session Tracking -----------------
                    self.tracker.observe(ip)

                    server = self.tracker.update()

                    if not server:
                        continue

                    server_region = self.resolver.get_region(server)

                    # ----------------- State Update -----------------
                    if server != self.current_server_ip:
                        self.current_server_ip = server
                        self.current_region = server_region

                        print(
                            f"[RegionAnalyzer] Detected server: {server} ({server_region})"
                        )

                        if callable(self.on_server_detected):
                            self.on_server_detected(server, server_region)

                except Exception as e:
                    print(f"[RegionAnalyzer] Error: {e}")

        finally:
            self._running = False
            print("[RegionAnalyzer] Stopped")

    # ----------------- Runtime State -----------------
    def get_state(self):
        return AnalyzerState(
            self.game_active,
            self.current_server_ip,
            self.current_region,
        )