import sys


class PacketSniffer:
    UNSUPPORTED_MESSAGE = "Packet sniffing is only supported on Windows."
    supported = sys.platform == "win32"

    def __init__(self, filter_expr="outbound and udp"):
        self.filter_expr = filter_expr
        self.handle = None
        self.pydivert = None

        if self.supported:
            import pydivert
            self.pydivert = pydivert

    def __enter__(self):
        if not self.supported:
            return self

        self.handle = self.pydivert.WinDivert(self.filter_expr)
        self.handle.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.handle is not None:
            try:
                self.handle.close()
            except Exception:
                pass
            self.handle = None

    def __iter__(self):
        if not self.supported:
            raise RuntimeError(self.UNSUPPORTED_MESSAGE)

        if self.handle is None:
            raise RuntimeError("PacketSniffer not started.")

        return iter(self.handle)

    def send(self, packet):
        if not self.supported:
            return

        handle = self.handle

        if handle is not None:
            try:
                handle.send(packet)
            except (OSError, RuntimeError):
                pass