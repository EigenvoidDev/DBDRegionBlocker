# DBDRegionSelector

[Dead by Daylight](https://deadbydaylight.com/) is an online asymmetric multiplayer survival horror video game developed and published by Canadian studio [Behaviour Interactive](https://www.bhvr.com/).

**DBDRegionSelector** is a desktop GUI tool that lets you control which AWS regions Dead by Daylight can connect to. It continuously measures connectivity and shows real-time details for each supported region, including:
- **Region Status:** Whether the region is **active (unblocked)** or **blocked**
- **Region Name and Code**
- **Ping Counts:** Succeeded vs. Failed pings
- **Last Ping Status:** Succeeded or Failed
- **Last Ping Latency**
- **Packet Loss Percentage**

The application also includes a live status panel that updates whenever you apply changes or restore default settings, so you always know what actions have been taken.

## Installation

### Option 1: Run from Source

If you are running the application from source (e.g., cloned from GitHub), ensure you have [Python 3.9 or later](https://www.python.org/downloads/) installed. Then install the required dependencies with pip:
```
pip install PyQt6 qasync
```
After installation, open a terminal, navigate to the project's root directory, and start the application with:
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
- On **Windows 8 and later**, you may also see a security warning. This happens because the application is not digitally signed. Windows uses code-signing certificates (which require a paid license) to verify publishers. Without one, the application is labeled as coming from an "unknown publisher".

Some antivirus software may also flag the application as suspicious or block the download. These detections are **false positives**. If the application is blocked from running, you may need to add it to your allowlist or exclusions.

## Usage

- **Unblock/Block Regions:** Check a region to **unblock** it, or uncheck to **block** it.
- **Apply Changes:** Applies and saves the current checkbox configuration to the `hosts` file.
- **Restore Defaults:** Resets all checkboxes to checked (all regions active) and updates the `hosts` file accordingly.
- **Status Panel:** Displays live updates whenever changes are applied or defaults are restored, providing feedback on modifications to the `hosts` file.

## Important Notes

### How Region Selection Works
Dead by Daylight determines which regions you can connect to when you log in, based on your latencies to all available regions. The game will choose only from the regions you have unblocked in this application, prioritizing the regions with the lowest latency.

### Blocking All Regions
If you block all regions, Dead by Daylight will still estimate your latency to every region using your location data and select one for matchmaking based on those estimates.

### US East (N. Virginia) Region Behavior
Even if you block **US East (N. Virginia)**, the game may still route some connections through this region, because both **Easy Anti-Cheat (EAC)** and **RTM services** are hosted there. As a result, N. Virginia cannot be fully blocked without disrupting core game functionality.

To reduce the chances of connecting to N. Virginia game servers, you can:
- Block nearby regions that are more likely to be selected by the matchmaking system.
- Retry matchmaking until you are placed in a different region.

## License

DBDRegionSelector is licensed under the [GNU General Public License v3.0 (GPLv3)](https://github.com/EigenvoidDev/DBDRegionSelector/blob/main/LICENSE).