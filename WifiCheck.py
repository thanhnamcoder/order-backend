import platform
import subprocess

def get_connected_wifi():
    system = platform.system()

    try:
        if system == "Windows":
            # Lệnh hiển thị thông tin Wi-Fi đang kết nối
            result = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"],
                encoding="utf-8",
                errors="ignore"
            )
            for line in result.split("\n"):
                if "SSID" in line and "BSSID" not in line:
                    return line.split(":", 1)[1].strip()

        elif system == "Darwin":  # macOS
            result = subprocess.check_output(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
                encoding="utf-8"
            )
            for line in result.split("\n"):
                if " SSID:" in line:
                    return line.split(":")[1].strip()

        elif system == "Linux":
            result = subprocess.check_output(
                ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                encoding="utf-8"
            )
            for line in result.split("\n"):
                if line.startswith("yes:"):
                    return line.split(":")[1]

        else:
            return "Unsupported OS"

    except subprocess.CalledProcessError:
        return "Error: Cannot get Wi-Fi info"

    return "Not connected"

wifi_name = get_connected_wifi()
print("Wi-Fi đang kết nối:", wifi_name)
