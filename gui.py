import asyncio
from datetime import datetime
import os
import sys

from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import qasync

from data.regions import REGIONS
import services.hosts_manager as hosts_manager
import services.region_latency_monitor as rlm
from services.region_status_service import RegionStatusService
from services.networking.packet_sniffer import PacketSniffer
from services.networking.region_analyzer import RegionAnalyzer

# ----------------- Utilities -----------------
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_stylesheet(path):
    with open(resource_path(path), "r", encoding="utf-8") as f:
        return f.read()


def create_label(text=""):
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def append_status(status_log, message, color):
    message = str(message).rstrip("\n")
    timestamp = f"[{datetime.now().strftime('%H:%M:%S')}] "

    cursor = status_log.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)

    timestamp_format = QTextCharFormat()
    timestamp_format.setForeground(QColor("#e0e0e0"))
    cursor.insertText(timestamp, timestamp_format)

    message_format = QTextCharFormat()
    message_format.setForeground(color)
    cursor.insertText(message + "\n", message_format)

    status_log.setTextCursor(cursor)
    status_log.ensureCursorVisible()


# ---------------------- GUI ----------------------
def run_gui():
    icon_path = resource_path("icons/app_icon.ico")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))

    window = QWidget()
    window.setWindowTitle("DBD Region Blocker v3.1.0")
    window.setWindowIcon(QIcon(icon_path))
    window.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.WindowMinimizeButtonHint
        | Qt.WindowType.WindowCloseButtonHint
        | Qt.WindowType.CustomizeWindowHint
    )
    window.setFixedSize(1100, 900)

    # Load QSS Stylesheet
    qss = load_stylesheet("style/styles.qss")
    app.setStyleSheet(qss)

    # Event Loop Setup
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Services
    status_service = RegionStatusService()
    analyzer = RegionAnalyzer()

    # Async Bridges
    async def fetch_status_async():
        return await asyncio.to_thread(status_service.fetch_status)

    # Feature Flags
    sniffer_supported = PacketSniffer.SUPPORTED

    # ---------------------- Layouts ----------------------
    main_layout = QVBoxLayout()

    # Header Layout
    header_frame = QFrame()
    header_layout = QHBoxLayout()

    current_region_label = create_label("Current Region: Unknown")
    current_region_label.setObjectName("currentRegionLabel")

    header_layout.addWidget(current_region_label)
    header_frame.setLayout(header_layout)

    main_layout.addWidget(header_frame)

    # Region Grid
    region_frame = QFrame()
    region_grid = QGridLayout()
    region_grid.setVerticalSpacing(15)

    headers = [
        "Active",
        "Region Name",
        "Region",
        "Online Status",
        "Succeeded",
        "Failed",
        "Last Ping Status",
        "Latency",
        "Packet Loss",
    ]

    # Header Row
    for column, header in enumerate(headers):
        header_label = create_label(header)
        header_label.setObjectName("headerLabel")
        region_grid.addWidget(header_label, 0, column)

    checkboxes = {}
    labels = {}

    # Data Rows
    for row, (region_code, region_data) in enumerate(REGIONS.items(), start=1):
        # Active Toggle
        checkbox = QCheckBox()
        region_grid.addWidget(checkbox, row, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        checkboxes[region_code] = checkbox

        # Identity
        region_grid.addWidget(create_label(region_data["name"]), row, 1)
        region_grid.addWidget(create_label(region_code), row, 2)

        # Online Status
        online_status_label = create_label("Unknown")
        region_grid.addWidget(online_status_label, row, 3)

        # Ping Statistics
        succeeded_label = create_label("0")
        failed_label = create_label("0")
        last_ping_status_label = create_label(rlm.PingStatus.INITIALIZING.value)
        latency_label = create_label("N/A")
        packet_loss_label = create_label("0%")

        region_grid.addWidget(succeeded_label, row, 4)
        region_grid.addWidget(failed_label, row, 5)
        region_grid.addWidget(last_ping_status_label, row, 6)
        region_grid.addWidget(latency_label, row, 7)
        region_grid.addWidget(packet_loss_label, row, 8)

        # Store references for live updates
        labels[region_code] = {
            "online_status": online_status_label,
            "succeeded": succeeded_label,
            "failed": failed_label,
            "last_ping_status": last_ping_status_label,
            "latency": latency_label,
            "packet_loss": packet_loss_label,
        }

    region_frame.setLayout(region_grid)
    main_layout.addWidget(region_frame)

    # Buttons Layout
    buttons_layout = QHBoxLayout()

    apply_changes_button = QPushButton("Apply Changes")
    restore_defaults_button = QPushButton("Restore Defaults")
    toggle_sniffer_button = QPushButton()
    toggle_sniffer_button.setEnabled(sniffer_supported)

    buttons_layout.addWidget(apply_changes_button)
    buttons_layout.addWidget(restore_defaults_button)
    buttons_layout.addWidget(toggle_sniffer_button)

    main_layout.addLayout(buttons_layout)

    # Status Log
    status_log = QTextEdit()
    status_log.setReadOnly(True)
    status_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    status_log.setObjectName("statusLog")
    main_layout.addWidget(status_log)

    window.setLayout(main_layout)

    # ---------------------- Hosts File Initialization ----------------------
    result = hosts_manager.initialize_hosts_file()

    if result == hosts_manager.HostsUpdateStatus.SUCCESS:
        append_status(
            status_log, "Hosts file initialized successfully.", QColor("#4caf50")
        )

    elif result == hosts_manager.HostsUpdateStatus.NO_CHANGES:
        append_status(
            status_log, "Hosts file is already up to date.", QColor("#ffa500")
        )

    elif result == hosts_manager.HostsUpdateStatus.PERMISSION_ERROR:
        append_status(
            status_log,
            "Administrator privileges required to initialize the hosts file. Please run the application as an administrator.",
            QColor("#ff5555"),
        )

    elif result == hosts_manager.HostsUpdateStatus.WRITE_ERROR:
        append_status(status_log, "Failed to initialize the hosts file.", QColor("#ff5555"))

    else:
        append_status(
            status_log,
            "An unexpected error occurred while initializing the hosts file.",
            QColor("#ff5555"),
        )

    # ---------------------- Load Region Settings ----------------------
    def sync_checkboxes():
        try:
            config = hosts_manager.load_config()
            regions = config.get("regions", {})

            for region_code, checkbox in checkboxes.items():
                checkbox.setChecked(not regions.get(region_code, False))

            append_status(
                status_log, "Configuration loaded successfully.", QColor("#4caf50")
            )

        except Exception:
            append_status(
                status_log,
                "Configuration not found or invalid. Default configuration created.",
                QColor("#ffa500"),
            )

    sync_checkboxes()

    # ---------------------- Packet Sniffer Initialization ----------------------
    if not sniffer_supported:
        append_status(
            status_log,
            "Packet sniffing is only supported on Windows.",
            QColor("#ffa500"),
        )

    def handle_sniffer_state(state):
        if state:
            append_status(status_log, "Packet sniffer enabled.", QColor("#4caf50"))
        else:
            if analyzer.sniffer_enabled:
                append_status(
                    status_log,
                    "Administrator privileges required to start packet sniffer. Please run the application as an administrator.",
                    QColor("#ff5555"),
                )
            else:
                append_status(status_log, "Packet sniffer disabled.", QColor("#ffa500"))

    analyzer.on_sniffer_state = handle_sniffer_state

    if hosts_manager.get_packet_sniffer_enabled():
        analyzer.enable_sniffer()

    # ---------------------- User Controls & State Management ----------------------
    def apply_changes():
        try:
            for region_code, checkbox in checkboxes.items():
                hosts_manager.set_region_block(region_code, not checkbox.isChecked())

            result = hosts_manager.apply_config_to_hosts()

            if result == hosts_manager.HostsUpdateStatus.SUCCESS:
                append_status(
                    status_log,
                    "Hosts file updated successfully. Restart Dead by Daylight for changes to apply.",
                    QColor("#4caf50"),
                )

            elif result == hosts_manager.HostsUpdateStatus.NO_CHANGES:
                append_status(
                    status_log, "Hosts file is already up to date.", QColor("#ffa500")
                )

            elif result == hosts_manager.HostsUpdateStatus.PERMISSION_ERROR:
                append_status(
                    status_log,
                    "Administrator privileges required to update the hosts file. Please run the application as an administrator.",
                    QColor("#ff5555"),
                )

            elif result == hosts_manager.HostsUpdateStatus.WRITE_ERROR:
                append_status(
                    status_log, "Failed to update the hosts file.", QColor("#ff5555")
                )

        except Exception:
            append_status(
                status_log,
                "An unexpected error occurred while applying changes.",
                QColor("#ff5555"),
            )

    def restore_defaults():
        try:
            for region_code, checkbox in checkboxes.items():
                checkbox.setChecked(True)
                hosts_manager.set_region_block(region_code, False)

            result = hosts_manager.apply_config_to_hosts()

            if result == hosts_manager.HostsUpdateStatus.SUCCESS:
                append_status(
                    status_log,
                    "Hosts file restored to default configuration. Restart Dead by Daylight for changes to apply.",
                    QColor("#4caf50"),
                )

            elif result == hosts_manager.HostsUpdateStatus.NO_CHANGES:
                append_status(
                    status_log,
                    "Hosts file is already in default state.",
                    QColor("#ffa500"),
                )

            elif result == hosts_manager.HostsUpdateStatus.PERMISSION_ERROR:
                append_status(
                    status_log,
                    "Administrator privileges required to update the hosts file. Please run the application as an administrator.",
                    QColor("#ff5555"),
                )

            elif result == hosts_manager.HostsUpdateStatus.WRITE_ERROR:
                append_status(
                    status_log, "Failed to update the hosts file.", QColor("#ff5555")
                )

        except Exception:
            append_status(
                status_log,
                "An unexpected error occurred while restoring defaults.",
                QColor("#ff5555"),
            )

    def toggle_sniffer():
        try:
            if analyzer.sniffer_enabled:
                analyzer.disable_sniffer()
                hosts_manager.set_packet_sniffer_enabled(False)

            else:
                analyzer.enable_sniffer()
                hosts_manager.set_packet_sniffer_enabled(True)

            update_sniffer_button_text()

        except Exception:
            append_status(
                status_log, "Failed to toggle packet sniffer.", QColor("#ff5555")
            )

    def update_sniffer_button_text():
        if not sniffer_supported:
            toggle_sniffer_button.setText("Packet Sniffer Unsupported")

        elif analyzer.sniffer_enabled:
            toggle_sniffer_button.setText("Disable Packet Sniffer")

        else:
            toggle_sniffer_button.setText("Enable Packet Sniffer")

    apply_changes_button.clicked.connect(apply_changes)
    restore_defaults_button.clicked.connect(restore_defaults)
    toggle_sniffer_button.clicked.connect(toggle_sniffer)

    update_sniffer_button_text()

    # ---------------------- Region Status Service ----------------------
    async def update_region_online_status():
        data = await fetch_status_async()

        for region_code, label in labels.items():
            state = data.get(region_code)

            if state is True:
                label["online_status"].setText("Online")

            elif state is False:
                label["online_status"].setText("Offline")

            else:
                label["online_status"].setText("Unknown")

    def trigger_region_online_status_update():
        asyncio.create_task(update_region_online_status())

    # ---------------------- Region Latency Monitor ----------------------
    results = {}
    ping_tasks = []

    # Monitor Initialization
    async def start_region_latency_monitor():
        nonlocal results, ping_tasks
        results, ping_tasks = await rlm.ping_all_regions_continuous()

    loop.create_task(start_region_latency_monitor())

    # Latency Color Mapping
    def get_ping_quality_color(ping_status_enum, latency=None):
        color = "#e0e0e0"

        if ping_status_enum == rlm.PingStatus.SUCCEEDED and latency is not None:
            quality_colors = {
                rlm.LatencyQuality.GOOD: "#4caf50",
                rlm.LatencyQuality.OK: "#ffa500",
                rlm.LatencyQuality.BAD: "#ff5555",
            }
            color = quality_colors.get(rlm.classify_latency(latency), color)

        elif ping_status_enum == rlm.PingStatus.ERROR:
            color = "#9e9e9e"

        return color

    # Latency UI Refresh
    def update_latency_ui():
        for region_code, label_set in labels.items():
            data = results.get(region_code)
            if data is None:
                continue

            succeeded = data.succeeded_count
            label_set["succeeded"].setText(str(succeeded))

            failed = data.failed_count
            label_set["failed"].setText(str(failed))

            last_ping_status = data.last_ping_status or rlm.PingStatus.INITIALIZING
            label_set["last_ping_status"].setText(last_ping_status.value)

            latency = data.last_ping_latency
            label_set["latency"].setText(
                f"{latency:.0f}ms" if latency is not None else "N/A"
            )

            packet_loss = data.packet_loss_percentage
            label_set["packet_loss"].setText(f"{packet_loss:.2f}%")

            color = get_ping_quality_color(last_ping_status, latency)
            label_set["latency"].setStyleSheet(f"color: {color}")

    # ---------------------- Event Handlers ----------------------
    class SignalBridge(QObject):
        server_detected = pyqtSignal(str, str)

    bridge = SignalBridge()

    def update_current_region_label(server, region):
        if not server or not region:
            current_region_label.setText("Current Region: Unknown")
        else:
            current_region_label.setText(f"Current Region: {region} ({server})")

    bridge.server_detected.connect(update_current_region_label)

    def on_server_detected(server, region):
        bridge.server_detected.emit(server, region)

    analyzer.on_server_detected = on_server_detected

    # ---------------------- Background Services Initialization ----------------------
    async def run_analyzer():
        await asyncio.to_thread(analyzer.run)

    analyzer_task = loop.create_task(run_analyzer())

    # ---------------------- Game State Change Detection ----------------------
    last_game_state = None

    def update_analyzer_log():
        nonlocal last_game_state

        game_running = analyzer.game_active

        if game_running != last_game_state:
            last_game_state = game_running

            if game_running:
                append_status(
                    status_log, "Dead by Daylight detected!", QColor("#4caf50")
                )
            else:
                append_status(
                    status_log,
                    "Waiting for Dead by Daylight to start...",
                    QColor("#e0e0e0"),
                )

    # ---------------------- UI Update Timers ----------------------
    latency_ui_timer = QTimer()
    latency_ui_timer.timeout.connect(update_latency_ui)
    latency_ui_timer.start(1000)

    analyzer_log_timer = QTimer()
    analyzer_log_timer.timeout.connect(update_analyzer_log)
    analyzer_log_timer.start(2000)

    region_online_status_timer = QTimer()
    region_online_status_timer.timeout.connect(trigger_region_online_status_update)
    region_online_status_timer.start(5000)

    # ---------------------- Clean Exit ----------------------
    def close_event(event):
        hosts_manager.reset_hosts_on_exit()
        analyzer.stop()

        for task in ping_tasks:
            task.cancel()

        analyzer_task.cancel()

        loop.call_soon(loop.stop)
        event.accept()

    window.closeEvent = close_event

    window.show()

    with loop:
        loop.run_forever()
