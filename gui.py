import os
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import REGIONS
from core.hosts_manager import (
    initialize_hosts_file,
    get_active_regions_from_hosts,
    update_hosts_file,
)
from core.region_latency_monitor import ping_all_regions, terminate_all_pings

# ==============
# Constants
# ==============
APP_VERSION = "v1.1.0"
ERROR_COLOR = "#ee4444"
ERROR_MESSAGE = "Administrator privileges required. Please run this application as an administrator."
SUCCESS_MESSAGE = "Please restart Dead by Daylight for the changes to take effect."

# ---------------------- Utilities ----------------------
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_stylesheet(path):
    with open(resource_path(path), "r", encoding="utf-8") as file:
        stylesheet = file.read()

    image_path = resource_path("images/chevron-down.png").replace("\\", "/")
    stylesheet = stylesheet.replace(
        "url(images/chevron-down.png)", f"url({image_path})"
    )

    return stylesheet


def format_active_regions_status(active_regions):
    total = len(REGIONS)
    if len(active_regions) in (0, total):
        return "All regions available."
    return ", ".join(f"{r} ({REGIONS[r]['region']})" for r in active_regions)


# ---------------------- GUI ----------------------
def run_gui():
    icon_path = resource_path("icons/app_icon.ico")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))

    window = QWidget()
    window.setWindowTitle(f"DBD Region Selector {APP_VERSION}")
    window.setWindowIcon(QIcon(icon_path))

    window.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.WindowMinimizeButtonHint
        | Qt.WindowType.WindowCloseButtonHint
        | Qt.WindowType.CustomizeWindowHint
    )

    window.setFixedSize(600, 640)

    # Load QSS Stylesheet
    qss = load_stylesheet("style/styles.qss")
    app.setStyleSheet(qss)

    # ---------------------- Layouts ----------------------
    main_layout = QVBoxLayout()

    # Title and Version
    title = QLabel("DBD Region Selector")
    title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    title.setObjectName("titleLabel")

    version = QLabel(f"{APP_VERSION}")
    version.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    version.setObjectName("versionLabel")

    main_layout.addWidget(title)
    main_layout.addWidget(version)

    # Initialize hosts file
    initialize_hosts_file()

    # Select Region Group
    region_group = QGroupBox("Select Region")
    region_layout = QVBoxLayout()

    region_dropdown = QComboBox()
    for region_name, region_data in REGIONS.items():
        region_dropdown.addItem(
            f"{region_name} ({region_data['region']})", userData=region_name
        )
    region_layout.addWidget(region_dropdown)

    buttons_layout = QHBoxLayout()
    set_button = QPushButton("Set Region")
    default_button = QPushButton("Set Default")
    buttons_layout.addWidget(set_button)
    buttons_layout.addWidget(default_button)
    region_layout.addLayout(buttons_layout)

    region_group.setLayout(region_layout)
    main_layout.addWidget(region_group)
    main_layout.addSpacing(10)

    # Selected Region Group
    selected_group = QGroupBox("Selected Region")
    selected_layout = QVBoxLayout()

    active_regions = get_active_regions_from_hosts()
    current_text = format_active_regions_status(active_regions)

    current_label = QLabel(current_text)
    selected_layout.addWidget(current_label)

    restart_label = QLabel("")
    restart_label.setVisible(False)
    selected_layout.addWidget(restart_label)

    selected_group.setLayout(selected_layout)
    main_layout.addWidget(selected_group)
    main_layout.addSpacing(10)

    # Ping Group
    ping_group = QGroupBox("Ping")
    ping_layout = QVBoxLayout()

    ping_output = QTextEdit()
    ping_output.setReadOnly(True)
    ping_output.setHtml("<i>Measuring latencies and packet loss...</i>")
    ping_output.setObjectName("pingOutput")
    ping_layout.addWidget(ping_output)

    ping_group.setLayout(ping_layout)
    main_layout.addWidget(ping_group)

    window.setLayout(main_layout)

    # ---------------------- Ping Management / Display Panel ----------------------
    results = ping_all_regions()

    def update_ping_display():
        lines = []
        for _, region_data in results.items():
            latency_ms = region_data["latency_ms"]
            packet_loss_percentage = region_data["packet_loss_percentage"]
            status = region_data["status"]

            color = {
                "good": "#4caf50",
                "ok": "#ffc107",
                "bad": "#e53935",
            }.get(status, "#dddddd")

            if latency_ms is None:
                line = f"<span style='color:{color};'>{region_data['region']}: N/A ms, N/A % packet loss</span>"
            else:
                line = f"<span style='color:{color};'>{region_data['region']}: {latency_ms:.0f}ms, {packet_loss_percentage:.2f}% packet loss</span>"
            lines.append(line)

        ping_output.setHtml("<br>".join(lines))

    # Timer for updating ping results
    timer = QTimer()
    timer.timeout.connect(update_ping_display)
    timer.start(5000)

    # ---------------------- Region Selection Panel ----------------------
    def handle_update_status(status, default=False):
        if status == "updated":
            restart_label.setStyleSheet("")
            restart_label.setText(SUCCESS_MESSAGE)
            restart_label.setVisible(True)
        elif status == "already_set":
            message = (
                "All regions already available." if default else "Region already set."
            )
            restart_label.setStyleSheet("")
            restart_label.setText(f"{message} {SUCCESS_MESSAGE}")
            restart_label.setVisible(True)
        else:
            restart_label.setStyleSheet(f"color: {ERROR_COLOR};")
            restart_label.setText(ERROR_MESSAGE)
            restart_label.setVisible(True)

    def on_set_region():
        selected_region = region_dropdown.currentData()
        status = update_hosts_file(active_region=selected_region, comment_all=False)

        active_regions = get_active_regions_from_hosts()
        current_label.setText(format_active_regions_status(active_regions))

        handle_update_status(status, default=False)

    set_button.clicked.connect(on_set_region)

    def on_set_default():
        status = update_hosts_file(comment_all=True)

        active_regions = get_active_regions_from_hosts()
        current_label.setText(format_active_regions_status(active_regions))

        handle_update_status(status, default=True)

    default_button.clicked.connect(on_set_default)

    # ---------------------- Application Exit Cleanup ----------------------
    app.aboutToQuit.connect(terminate_all_pings)

    window.show()
    sys.exit(app.exec())