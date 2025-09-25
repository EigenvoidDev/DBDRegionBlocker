# DBDRegionSelector

[Dead by Daylight](https://deadbydaylight.com/) is an online asymmetric multiplayer survival horror video game developed and published by Canadian studio [Behaviour Interactive](https://www.bhvr.com/).

**DBDRegionSelector** is a desktop GUI tool that lets you manage which AWS regions Dead by Daylight can connect to. It displays real-time latency and packet loss metrics for all supported regions and provides a simple interface for blocking or unblocking specific regions using `hosts` file rules.

## Installation

### Option 1: Run from Source

If you are running the application from source (e.g., cloned from GitHub), ensure you have [Python 3.9 or later](https://www.python.org/downloads/) installed. Then install the required dependencies with pip:
```
pip install PyQt6
```
After installation, open a terminal, navigate to the project’s root directory, and start the application with:
```
python main.py
```

**Note:** Changing region settings requires administrator (or root) privileges to modify the system `hosts` file.
- **Windows:** Run the terminal as an administrator before executing the script.
- **macOS/Linux:** Run the script with `sudo`:
```
sudo python3 main.py
```

### Option 2: Download Prebuilt Release

If you are on **Windows**, download the prebuilt release from the [Releases page](https://github.com/EigenvoidDev/DBDRegionSelector/releases). Once downloaded, simply double-click the file to launch the application.

#### Windows Security Warnings

This application requires administrator permissions to modify the system `hosts` file, which is needed to block or unblock specific Dead by Daylight AWS regions.
- On **Windows Vista and later**, a User Account Control (UAC) prompt will appear when you launch the application.
- On **Windows 8 and later**, you may also encounter a SmartScreen warning because the application is unsigned.

This application is not digitally signed since code-signing certificates require a paid license. As a result, Windows may list it as coming from an "unknown publisher".

Some antivirus software may also flag the application as suspicious or block the download. These detections are **false positives**. If the application is blocked from running, you may need to add it to your allowlist or exclusions.

## Usage

- **Select Region:** Use the dropdown at the top of the interface to choose an AWS region.
- **Set Region:** Click the **Set Region** button to block all other regions except the selected one.
- **Set Default:** Click the **Set Default** button to unblock all regions and restore the default configuration.
- **Ping:** At the bottom of the interface, the ping section updates every 5 seconds with real-time latency and packet loss metrics for all supported regions.

## Important Note on US East (N. Virginia) Region

Even if you block **US East (N. Virginia)**, the game may still route some connections through that region, because both **Easy Anti-Cheat (EAC)** and **RTM services** are hosted there. As a result, N. Virginia cannot be fully blocked without disrupting core game functionality.

To reduce the chances of connecting to N. Virginia game servers, you can try:
- Blocking nearby regions that are more likely to be selected by the matchmaking system.
- Retrying matchmaking until you are placed in a different region.

## License

DBDRegionSelector is licensed under the [GNU General Public License v3.0 (GPLv3)](https://github.com/EigenvoidDev/DBDRegionSelector/blob/main/LICENSE).