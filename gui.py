import asyncio
from datetime import datetime
import os
import sys

from PyQt6.QtCore import Qt, QTimer
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

from config import REGIONS
from core import hosts_manager
import core.region_latency_monitor as rlm

# ---------------------- Utilities ----------------------
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_stylesheet(path):
    with open(resource_path(path), "r", encoding="utf-8") as file:
        stylesheet = file.read()
    return stylesheet


def create_centered_label(text=""):
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setProperty("centered", True)
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
    window.setWindowTitle("DBD Region Selector v2.0.0")
    window.setWindowIcon(QIcon(icon_path))

    window.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.WindowMinimizeButtonHint
        | Qt.WindowType.WindowCloseButtonHint
        | Qt.WindowType.CustomizeWindowHint
    )

    window.setFixedSize(1475, 685)

    # Load QSS Stylesheet
    qss = load_stylesheet("style/styles.qss")
    app.setStyleSheet(qss)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # ---------------------- Layouts ----------------------
    main_layout = QHBoxLayout()
    left_layout = QVBoxLayout()
    right_layout = QVBoxLayout()

    # ---------------------- Left Side: Region Grid and Buttons ----------------------
    regions_title = create_centered_label("Regions")
    regions_title.setObjectName("regionsTitle")
    left_layout.addWidget(regions_title)

    # Region Grid
    region_grid = QGridLayout()
    region_grid.setHorizontalSpacing(15)
    region_grid.setVerticalSpacing(18)

    headers = [
        "Active",
        "Region Name",
        "Region",
        "Succeeded",
        "Failed",
        "Last Ping Status",
        "Latency",
        "Packet Loss",
    ]
    for col, header in enumerate(headers):
        label = create_centered_label(header)
        label.setProperty("header", True)
        region_grid.addWidget(label, 0, col)

    checkboxes = {}
    labels = {}

    for row, (region_name, region_data) in enumerate(REGIONS.items(), start=1):
        checkbox = QCheckBox()
        region_grid.addWidget(checkbox, row, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        checkboxes[region_name] = checkbox

        region_grid.addWidget(create_centered_label(region_name), row, 1)
        region_grid.addWidget(create_centered_label(region_data["region"]), row, 2)

        succeeded_label = create_centered_label("0")
        failed_label = create_centered_label("0")
        last_ping_status_label = create_centered_label(
            rlm.PingStatus.INITIALIZING.value
        )
        latency_label = create_centered_label("N/A")
        packet_loss_label = create_centered_label("0%")

        region_grid.addWidget(succeeded_label, row, 3)
        region_grid.addWidget(failed_label, row, 4)
        region_grid.addWidget(last_ping_status_label, row, 5)
        region_grid.addWidget(latency_label, row, 6)
        region_grid.addWidget(packet_loss_label, row, 7)

        labels[region_name] = {
            "succeeded": succeeded_label,
            "failed": failed_label,
            "last_ping_status": last_ping_status_label,
            "latency": latency_label,
            "packet_loss": packet_loss_label,
        }

    region_frame = QFrame()
    region_frame.setObjectName("regionFrame")
    region_frame.setLayout(region_grid)
    left_layout.addWidget(region_frame)
    left_layout.addStretch()

    # Buttons
    button_layout = QHBoxLayout()
    apply_changes_button = QPushButton("Apply Changes")
    restore_defaults_button = QPushButton("Restore Defaults")
    button_layout.addWidget(apply_changes_button)
    button_layout.addWidget(restore_defaults_button)
    left_layout.addLayout(button_layout)

    # ---------------------- Right Side: Status Log ----------------------
    status_title = create_centered_label("Status")
    status_title.setObjectName("statusTitle")
    right_layout.addWidget(status_title)

    status_log = QTextEdit()
    status_log.setReadOnly(True)
    status_log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    status_log.setObjectName("statusLog")
    right_layout.addWidget(status_log)

    # ---------------------- Final Layout ----------------------
    main_layout.addLayout(left_layout)
    main_layout.addLayout(right_layout)

    window.setLayout(main_layout)

    # ---------------------- Hosts File Operations ----------------------
    # Initialize hosts file
    if hosts_manager.initialize_hosts_file():
        append_status(
            status_log, "Hosts file initialized successfully.", QColor("#4caf50")
        )
    else:
        append_status(
            status_log,
            "Failed to initialize hosts file. Run as administrator.",
            QColor("#ff5555"),
        )

    # Sync checkboxes with hosts file
    def sync_checkboxes():
        try:
            with open(hosts_manager.get_hosts_path(), "r", encoding="utf-8") as f:
                in_block = False
                for line in f:
                    stripped = line.strip()
                    if stripped == hosts_manager.HOSTS_SECTION_START:
                        in_block = True
                        continue
                    elif stripped == hosts_manager.HOSTS_SECTION_END:
                        break
                    if in_block:
                        for region_name, checkbox in checkboxes.items():
                            hostname = hosts_manager.REGIONS[region_name][
                                "udp_ping_beacon_endpoint"
                            ]
                            if f"# 0.0.0.0 {hostname}" in stripped:
                                checkbox.setChecked(True)
                            elif f"0.0.0.0 {hostname}" in stripped:
                                checkbox.setChecked(False)
        except PermissionError:
            append_status(
                status_log,
                "Cannot read hosts file. Run as administrator.",
                QColor("#ff5555"),
            )
        except FileNotFoundError:
            append_status(status_log, "Hosts file not found.", QColor("#ff5555"))

    sync_checkboxes()

    def apply_changes():
        active = [name for name, checkbox in checkboxes.items() if checkbox.isChecked()]
        status = hosts_manager.update_hosts_file(
            active_regions=active, all_regions_active=False
        )
        if status.name in ("UPDATE_SUCCESS", "ALREADY_UP_TO_DATE"):
            append_status(
                status_log,
                "Hosts file updated successfully. Restart Dead by Daylight for changes to take effect.",
                QColor("#4caf50"),
            )
        elif status.name == "PERMISSION_ERROR":
            append_status(
                status_log, "Permission error: Run as administrator.", QColor("#ff5555")
            )
        elif status.name == "WRITE_ERROR":
            append_status(
                status_log, "Failed to write to hosts file.", QColor("#ff5555")
            )
        sync_checkboxes()

    def restore_defaults():
        status = hosts_manager.update_hosts_file(
            active_regions=[], all_regions_active=True
        )
        if status.name in ("UPDATE_SUCCESS", "ALREADY_UP_TO_DATE"):
            append_status(
                status_log,
                "Hosts file restored to default configuration. Restart Dead by Daylight for changes to take effect.",
                QColor("#4caf50"),
            )
            sync_checkboxes()
        elif status.name == "PERMISSION_ERROR":
            append_status(
                status_log, "Permission error: Run as administrator.", QColor("#ff5555")
            )
        elif status.name == "WRITE_ERROR":
            append_status(
                status_log, "Failed to write to hosts file.", QColor("#ff5555")
            )

    apply_changes_button.clicked.connect(apply_changes)
    restore_defaults_button.clicked.connect(restore_defaults)

    # ---------------------- Async Ping Updates ----------------------
    results = {}
    ping_tasks = []

    def get_ping_status_color(ping_status_enum, latency=None):
        # Default Color
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

    def refresh_region_stats():
        for region_name, stat_labels in labels.items():
            data = results.get(region_name)
            if not data:
                continue

            # Basic Stats
            stat_labels["succeeded"].setText(str(data.get("succeeded_count", 0)))
            stat_labels["failed"].setText(str(data.get("failed_count", 0)))

            ping_status_enum = data.get("last_ping_status", rlm.PingStatus.INITIALIZING)
            stat_labels["last_ping_status"].setText(
                ping_status_enum.value
                if isinstance(ping_status_enum, rlm.PingStatus)
                else str(ping_status_enum)
            )

            latency = data.get("last_ping_latency")
            stat_labels["latency"].setText(
                f"{latency:.0f}ms" if latency is not None else "N/A"
            )
            packet_loss = data.get("packet_loss_percentage", 0.0)
            stat_labels["packet_loss"].setText(f"{packet_loss:.2f}%")

            # Apply color based on latency quality
            color = get_ping_status_color(ping_status_enum, latency)
            stat_labels["latency"].setStyleSheet(f"color: {color}")

    timer = QTimer()
    timer.timeout.connect(refresh_region_stats)
    timer.start(5000)

    # Launch asynchronous tasks to continuously ping all regions
    async def start_continuous_pings():
        nonlocal ping_tasks
        ping_tasks = await rlm.ping_all_regions_continuous(results)

    asyncio.ensure_future(start_continuous_pings())

    # Window Close Handler
    def on_close(event):
        for task in ping_tasks:
            task.cancel()

        async def cleanup():
            await asyncio.gather(*ping_tasks, return_exceptions=True)

        asyncio.ensure_future(cleanup())

        event.accept()

    window.closeEvent = on_close

    window.show()
    loop.run_forever()