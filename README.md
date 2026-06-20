# DBDRegionBlocker

[Dead by Daylight](https://deadbydaylight.com/) is an online asymmetric multiplayer survival horror video game developed and published by Canadian studio [Behaviour Interactive](https://www.bhvr.com/).

**DBDRegionBlocker** is a desktop GUI tool that lets you selectively block or allow Dead by Daylight AWS regions. It provides real-time match server detection, region availability status, and live network metrics including latency, packet loss, ping reliability, and last ping status.

## Installation

### Option 1: Run from Source

If you want to run the application from source, ensure you have [Python 3.10 or later](https://www.python.org/downloads/) installed. Then open a terminal and run:
```
git clone https://github.com/EigenvoidDev/DBDRegionBlocker.git
cd DBDRegionBlocker
```
Install the required dependencies:
```
pip install -r requirements.txt
```
Finally, start the application:
```
python main.py
```

**Note:** This application requires administrator (or root) privileges to modify the system `hosts` file and perform packet capture.
- **Windows:** Run the terminal as an administrator before executing the script.
- **macOS/Linux:** Run the script with `sudo`:
```
sudo python3 main.py
```

### Option 2: Download Prebuilt Release

If you are on **Windows**, download the prebuilt release from the [Releases page](https://github.com/EigenvoidDev/DBDRegionBlocker/releases). Once downloaded, simply double-click the file to launch the application.

#### Windows Security Warnings

This application requires administrator privileges, which will trigger a User Account Control (UAC) prompt when launched on Windows.

On **Windows 8 and later**, you may also see a security warning when launching the application. This occurs because the application is not digitally signed, and Windows relies on code-signing to verify the identity of software publishers. Since obtaining a code-signing certificate requires a paid license, unsigned applications are labeled as coming from an "unknown publisher".

Some antivirus software may also flag the application as suspicious or block the download. These detections are **false positives**. If the application is blocked from running, you may need to add it to your allowlist or exclusions.

## Usage

- **Region Control:** Each region has a checkbox under the **Active** column. Checked regions are allowed, while unchecked regions are blocked.
- **Apply Changes:** Applies the current region configuration and updates the `hosts` file.
- **Restore Defaults:** Resets all regions to allowed (checked) and updates the `hosts` file.
- **Game Detection:** Automatically detects when Dead by Daylight is running.
- **Packet Capture:** Enables or disables real-time match server detection.
- **Status Log:** Displays live updates for application events such as applying changes, restoring defaults, game detection events, and packet capture state (enabled/disabled).

## Region Availability

Region availability is retrieved from the [Dead by Queue Regions API](https://api2.deadbyqueue.com/regions) and indicates whether a region is currently online or offline.

This information is updated periodically and displayed alongside each region in the application.

## Important Notes

### How Region Selection Works
Dead by Daylight determines which regions you can connect to when you log in based on your latency to all available regions. The game will only select from regions you have allowed in this application, prioritizing those with the lowest latency.

### Blocking All Regions
If you block all regions, Dead by Daylight will still select a matchmaking region based on latency estimates using your location data.

### US East (N. Virginia) Region Behavior
Even if you block **US East (N. Virginia)**, some game-related traffic may still be routed through this region because certain services, including **Easy Anti-Cheat (EAC)** and **RTM** infrastructure, are hosted there. While this does not necessarily affect matchmaking region selection, N. Virginia cannot be completely blocked without impacting core game functionality.

## Limitations

- **Internet connection required for:**
  - Region availability data
  - AWS IP range data used for region resolution
  - Latency measurements and connectivity checks
  - Match server detection

- Packet capture is only supported on Windows.

- In rare cases, the application may not fully terminate on exit, leaving a background process running.
  - This does not affect functionality or future runs of the application.
  - If needed, terminate it manually via Task Manager (Windows) or `kill <pid>` (macOS/Linux).

## Supported Regions

| Region         | Location      |
|----------------|---------------|
| us-east-1      | N. Virginia   |
| us-east-2      | Ohio          |
| us-west-1      | N. California |
| us-west-2      | Oregon        |
| ca-central-1   | Montréal      |
| eu-west-1      | Dublin        |
| eu-west-2      | London        |
| eu-central-1   | Frankfurt     |
| ap-south-1     | Mumbai        |
| ap-east-1      | Hong Kong     |
| ap-northeast-1 | Tokyo         |
| ap-northeast-2 | Seoul         |
| ap-southeast-1 | Singapore     |
| ap-southeast-2 | Sydney        |
| sa-east-1      | São Paulo     |

## License

DBDRegionBlocker is licensed under the [GNU General Public License v3.0 (GPLv3)](https://github.com/EigenvoidDev/DBDRegionBlocker/blob/main/LICENSE).
