import sys


class PacketSniffer:
    SUPPORTED = sys.platform == "win32"

    def __init__(self, filter_expr="outbound and udp"):
        self.filter_expr = filter_expr
        self.handle = None
        self.pydivert = None

        if self.SUPPORTED:
            import pydivert

            self.pydivert = pydivert

    def __enter__(self):
        if not self.SUPPORTED:
            return self

        self.handle = self.pydivert.WinDivert(
            self.filter_expr, flags=self.pydivert.Flag.SNIFF
        )

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
        if self.handle is None:
            raise RuntimeError(
                'PacketSniffer not started. Use "with PacketSniffer() as sniffer".'
            )
        return iter(self.handle)
