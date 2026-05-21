# DBDRegionBlocker

[Dead by Daylight](https://deadbydaylight.com/) is an online asymmetric multiplayer survival horror video game developed and published by Canadian studio [Behaviour Interactive](https://www.bhvr.com/).

**DBDRegionBlocker** is a desktop GUI tool that lets you selectively block or allow Dead by Daylight AWS regions. It provides real-time detection of the active match server, along with region availability status and live network metrics including ping reliability, last ping status, latency, and packet loss.

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

**Note:** This application requires administrator (or root) privileges to perform packet capture and modify the system `hosts` file.
- **Windows:** Run the terminal as an administrator before executing the script.
- **macOS/Linux**: Run the script with `sudo`:
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
- **Automatic Detection:** The application automatically detects when Dead by Daylight is running and identifies the active match server in real time using packet capture.
- **Status Log:** Displays live updates for application events such as applying changes, restoring defaults, and Dead by Daylight running status updates.

## Region Availability

Region availability status is retrieved from the [Dead by Queue Regions API](https://api2.deadbyqueue.com/regions) and indicates whether a region is currently online or offline.

This information is updated periodically and displayed alongside each region in the application.

## Important Notes

### How Region Selection Works
Dead by Daylight determines which regions you can connect to when you log in based on your latency to all available regions. The game will only select from regions you have allowed in this application, prioritizing those with the lowest latency.

### Blocking All Regions
If you block all regions, Dead by Daylight will still estimate your latency to each region using your location data and select one for matchmaking based on those estimates.

### US East (N. Virginia) Region Behavior
Even if you block **US East (N. Virginia)**, the game may still route some connections through this region because both **Easy Anti-Cheat (EAC)** and **RTM services** are hosted there. As a result, N. Virginia cannot be fully blocked without affecting core game functionality.

To reduce the chances of connecting to N. Virginia game servers:
- Block nearby regions that are more likely to be selected by the matchmaking system.
- Retry matchmaking until you are placed in a different region.

## Limitations

- Requires an active internet connection for:
  - Fetching AWS region availability data
  - Resolving AWS region data
  - Performing region status checks and latency/ping measurements
  - Packet-based server detection for identifying the active match server IP address

- The application must remain running for region blocking and server detection to function correctly.

- Packet capture functionality is only supported on Windows.

- The application may occasionally not fully terminate on exit, leaving a background process running. This is rare and does not affect functionality. If this occurs, the process can be manually terminated via Task Manager (Windows) or `kill <pid>` (macOS/Linux). This does not affect future runs of the application.

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