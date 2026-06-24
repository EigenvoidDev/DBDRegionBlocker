from dataclasses import dataclass
import ipaddress
import queue
import threading
import time

import psutil

from .aws_region_resolver import AWSRegionResolver
from .packet_sniffer import PacketSniffer
from .session_tracker import SessionTracker


@dataclass
class AnalyzerState:
    game_active: bool
    current_server_ip: str | None
    current_region: str | None


class RegionAnalyzer:
    def __init__(self):
        # Core Services
        self.resolver = AWSRegionResolver()
        self.tracker = SessionTracker()

        # Packet Queue
        self.packet_queue = queue.Queue(maxsize=500)

        # State Tracking
        self.game_active = False
        self.current_server_ip = None
        self.current_region = None

        # Callbacks
        self.on_server_detected = None
        self.on_sniffer_state = None

        # Runtime State
        self._running = False

        # Game Detection
        self._game_thread = None
        self._game_stop_event = threading.Event()

        # Sniffer Configuration
        self._sniffer_supported = PacketSniffer.SUPPORTED
        self.sniffer_enabled = False
        self._sniffer_start_requested = False

        # Sniffer Thread
        self._sniffer_thread = None
        self._sniffer = None

    # ----------------- Game Detection -----------------
    def _game_worker(self):
        last_state = None

        while not self._game_stop_event.is_set():
            running = False

            for proc in psutil.process_iter(["name"]):
                try:
                    if "DeadByDaylight" in (proc.info["name"] or ""):
                        running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if running != last_state:
                self.game_active = running
                last_state = running

                self.tracker.reset()

                if not running:
                    self.current_server_ip = None
                    self.current_region = None

                    if callable(self.on_server_detected):
                        self.on_server_detected("", "")

            time.sleep(1.0)

    def _start_game_thread(self):
        if self._game_thread and self._game_thread.is_alive():
            return

        self._game_stop_event.clear()

        self._game_thread = threading.Thread(
            target=self._game_worker,
            daemon=True,
        )
        self._game_thread.start()

    def _stop_game_thread(self):
        self._game_stop_event.set()

    # ----------------- Sniffer Control -----------------
    def enable_sniffer(self):
        if not self._sniffer_supported or self.sniffer_enabled:
            return False

        self.sniffer_enabled = True

        if not self._running:
            self._sniffer_start_requested = True
            return True

        self._reset_state()
        self._start_sniffer_thread()
        return True

    def disable_sniffer(self):
        if not self.sniffer_enabled and not self._sniffer_thread:
            return False

        self.sniffer_enabled = False
        self._sniffer_start_requested = False

        self._reset_state()

        if callable(self.on_server_detected):
            self.on_server_detected("", "")

        if self._sniffer_thread and self._sniffer_thread.is_alive():
            self._sniffer_thread.join(timeout=2)

        self._sniffer_thread = None
        self._sniffer = None

        return True

    def _reset_state(self):
        self.tracker = SessionTracker()
        self.packet_queue = queue.Queue(maxsize=500)

        self.current_server_ip = None
        self.current_region = None

    def _start_sniffer_thread(self):
        if not self._running:
            return

        if self._sniffer_thread and self._sniffer_thread.is_alive():
            return

        self._sniffer_thread = threading.Thread(
            target=self._sniffer_worker,
            daemon=True,
        )
        self._sniffer_thread.start()

    # ----------------- Sniffer Worker -----------------
    def _sniffer_worker(self):
        if not self._sniffer_supported:
            return

        print("[PacketSniffer] Started")

        try:
            with PacketSniffer() as sniffer:
                self._sniffer = sniffer

                if callable(self.on_sniffer_state):
                    self.on_sniffer_state(True)

                for packet in sniffer:
                    if not self._running or not self.sniffer_enabled:
                        break

                    try:
                        if packet.is_outbound and packet.udp:
                            ip = packet.dst_addr

                            try:
                                self.packet_queue.put_nowait(ip)
                            except queue.Full:
                                try:
                                    self.packet_queue.get_nowait()
                                except queue.Empty:
                                    pass
                                self.packet_queue.put_nowait(ip)

                    except Exception as e:
                        print(f"[PacketSniffer] Packet Error: {e}")

        except (OSError, RuntimeError) as e:
            if getattr(e, "winerror", None) != 995:
                print(f"[PacketSniffer] Capture Error: {e}")

        finally:
            self._sniffer = None

            if callable(self.on_sniffer_state):
                self.on_sniffer_state(False)

            print("[PacketSniffer] Stopped")

    # ----------------- Main Loop -----------------
    def run(self):
        if self._running:
            print("[RegionAnalyzer] Already running")
            return

        print("[RegionAnalyzer] Started")

        self._running = True
        self.resolver.load()

        self._start_game_thread()

        if self.sniffer_enabled or self._sniffer_start_requested:
            self._sniffer_start_requested = False
            self._start_sniffer_thread()

        try:
            while self._running:
                try:
                    ip = self.packet_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if not self.game_active:
                    continue

                try:
                    if ipaddress.ip_address(ip).version != 4:
                        continue
                except ValueError:
                    continue

                packet_region = self.resolver.get_region(ip)
                if not packet_region:
                    continue

                self.tracker.observe(ip)

                server = self.tracker.evaluate_current_server()
                if not server:
                    continue

                server_region = self.resolver.get_region(server)

                if server != self.current_server_ip:
                    self.current_server_ip = server
                    self.current_region = server_region

                    print(
                        f"[RegionAnalyzer] Detected server: {server} ({server_region})"
                    )

                    if callable(self.on_server_detected):
                        self.on_server_detected(server, server_region)

        finally:
            self.stop()
            print("[RegionAnalyzer] Stopped")

    # ----------------- Stop / Cleanup -----------------
    def stop(self):
        self._running = False
        self.disable_sniffer()
        self._stop_game_thread()

    # ----------------- State -----------------
    def get_state(self):
        return AnalyzerState(
            self.game_active,
            self.current_server_ip,
            self.current_region,
        )
