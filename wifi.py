# pip install pywifi psutil
import time
import socket
import psutil
import pywifi
from pywifi import const

def get_ipv4_address() -> str:
    """Lấy địa chỉ IPv4 hiện tại (bỏ qua localhost)."""
    addrs = psutil.net_if_addrs()
    for iface_addrs in addrs.values():
        for addr in iface_addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                return addr.address
    return "Không tìm thấy IPv4 Address"

def connect_wifi_psk(ssid: str, password: str, iface_index: int = 0, timeout: int = 25, hidden: bool = False) -> bool:
    """
    Kết nối Wi-Fi kiểu WPA/WPA2 (PSK).
    Có thể kết nối tới mạng ẩn (hidden SSID) nếu hidden=True.
    """
    wifi = pywifi.PyWiFi()
    ifaces = wifi.interfaces()
    if not ifaces:
        raise RuntimeError("Không tìm thấy interface WiFi")
    if iface_index >= len(ifaces):
        raise IndexError("iface_index ngoài phạm vi")
    iface = ifaces[iface_index]

    print(f"🔗 Đang cố gắng kết nối tới Wi-Fi: {ssid} (hidden={hidden})...")

    # Ngắt kết nối trước khi tạo profile mới
    try:
        iface.disconnect()
    except Exception:
        pass
    time.sleep(1)

    profile = pywifi.Profile()
    profile.ssid = ssid
    profile.hidden = hidden                     # 🔸 QUAN TRỌNG: đánh dấu là mạng ẩn
    profile.auth = const.AUTH_ALG_OPEN
    profile.akm.append(const.AKM_TYPE_WPA2PSK)  # WPA2-PSK
    profile.cipher = const.CIPHER_TYPE_CCMP
    profile.key = password

    iface.remove_all_network_profiles()
    tmp_profile = iface.add_network_profile(profile)

    iface.connect(tmp_profile)
    start = time.time()
    while time.time() - start < timeout:
        if iface.status() == const.IFACE_CONNECTED:
            ipv4 = get_ipv4_address()
            print(f"\n✅ Đã kết nối thành công!")
            print(f"📶 Wi-Fi Name (SSID): {ssid}")
            print(f"🌐 IPv4 Address: {ipv4}\n")
            return True
        time.sleep(0.5)

    # Timeout
    try:
        iface.disconnect()
    except Exception:
        pass
    print("❌ Kết nối thất bại (timeout).")
    return False


# =========================
# Ví dụ sử dụng:
# =========================

# Nếu mạng là **mạng ẩn**, đặt hidden=True
success = connect_wifi_psk("MOT", "circlek@vietnam", hidden=True)

# Nếu là mạng bình thường, có thể hidden=False
# success = connect_wifi_psk("CoGiHot", "C!rcleK@24h365n", hidden=False)

print("Connected" if success else "Failed")
