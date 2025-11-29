import requests
from typing import Optional
import re
from login_utils import get_login_info

def fetch_login_token(url: str, session: Optional[requests.Session] = None, timeout: int = 10) -> Optional[str]:
    s = session or requests.Session()
    resp = s.get(url, timeout=timeout)
    resp.raise_for_status()
    html = resp.text

    patterns = [
        r'name=["\']__RequestVerificationToken["\']\s+type=["\']hidden["\']\s+value=["\']([^"\']+)["\']',
        r'<input[^>]*name=["\']__RequestVerificationToken["\'][^>]*value=["\']([^"\']+)["\'][^>]*>',
        r'value=["\']([^"\']+)["\']\s+name=["\']__RequestVerificationToken["\']',
    ]

    for p in patterns:
        m = re.search(p, html, flags=re.IGNORECASE)
        if m:
            return m.group(1)

    # fallback BeautifulSoup
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        inp = soup.find("input", attrs={"name": "__RequestVerificationToken"})
        if inp and inp.has_attr("value"):
            return inp["value"]
    except:
        pass

    return None


def login(url_login: str, username: str, password: str) -> requests.Session:
    """
    Tự động GET token → POST login.
    Return session nếu login OK, raise error nếu fail.
    """

    session = requests.Session()

    # 1) GET token
    token = fetch_login_token(url_login, session=session)
    if not token:
        raise RuntimeError("Không lấy được __RequestVerificationToken")

    # print("[+] Token:", token)

    # 2) Chuẩn bị payload
    payload = {
        "__RequestVerificationToken": token,
        "UserName": username,
        "PassWord": password,
    }

    # Quan trọng: cần gửi headers như trình duyệt thật
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "http://storeportal.circlek.com.vn:82",
        "Referer": url_login,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    # 3) POST login
    resp = session.post(url_login, data=payload, headers=headers)

    # Check login success
    if "Logout" in resp.text or resp.url != url_login:
        print("[+] LOGIN THÀNH CÔNG!")
    else:
        # print("[-] LOGIN FAIL")
        # print("Response:", resp.text[:300])
        raise RuntimeError("Login failed")

    return session

def get_menu(session: requests.Session):
    url = "http://storeportal.circlek.com.vn:82/HHT/Menu"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "http://storeportal.circlek.com.vn:82/HHT/Index",
    }

    resp = session.get(url, headers=headers)

    # print("[+] GET /HHT/Menu status:", resp.status_code)

    # # In trước 500 ký tự để kiểm tra nội dung
    # print(resp.text)

    return resp.text
def get_planogram_token(session: requests.Session) -> str:
    """
    GET trang Planogram và lấy __RequestVerificationToken từ HTML.
    """
    url = "http://storeportal.circlek.com.vn:82/HHT/Mers/Planogram"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "http://storeportal.circlek.com.vn:82/HHT/Menu",
    }

    resp = session.get(url, headers=headers)
    resp.raise_for_status()

    html = resp.text

    # Dùng lại regex trong fetch_login_token
    patterns = [
        r'name=["\']__RequestVerificationToken["\']\s+type=["\']hidden["\']\s+value=["\']([^"\']+)["\']',
        r'<input[^>]*name=["\']__RequestVerificationToken["\'][^>]*value=["\']([^"\']+)["\'][^>]*>',
        r'value=["\']([^"\']+)["\']\s+name=["\']__RequestVerificationToken["\']',
    ]

    for p in patterns:
        m = re.search(p, html, flags=re.IGNORECASE)
        if m:
            token = m.group(1)
            # print("[+] Planogram Token:", token)
            return token

    # fallback
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        inp = soup.find("input", attrs={"name": "__RequestVerificationToken"})
        if inp and inp.has_attr("value"):
            token = inp["value"]
            # print("[+] Planogram Token:", token)
            return token
    except:
        pass

    raise RuntimeError("Không tìm thấy __RequestVerificationToken trong Planogram HTML")

def post_planogram_view(session: requests.Session, token: str):
    url = "http://storeportal.circlek.com.vn:82/HHT/Mers/Planogram"
    store_code = get_login_info("store_cd")
    payload = {
        "__RequestVerificationToken": token,
        "FileName": "",
        "StoreCode": store_code,
        "action:Planogram": "View"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "http://storeportal.circlek.com.vn:82/HHT/Mers/Planogram",
    }

    resp = session.post(url, data=payload, headers=headers)

    # print("[+] POST Planogram View:", resp.status_code)
    # print(resp.text)  # In trước 500 ký tự để xem nội dung trả về

    return resp

def post_planogram_read(session: requests.Session):
    url = "http://storeportal.circlek.com.vn:82/HHT/Mers/Planogram_Read"

    payload = {
        "sort": "",
        "group": "",
        "filter": "",
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "http://storeportal.circlek.com.vn:82/HHT/Mers/Planogram",
        "X-Requested-With": "XMLHttpRequest",  # Quan trọng cho API Kendo!
    }

    resp = session.post(url, data=payload, headers=headers)

    # print("[+] POST Planogram_Read:", resp.status_code)

    # In JSON trả về
    try:
        json_data = resp.json()
        # print("[+] JSON trả về (preview):")
        # print(json_data)
        return json_data
    except Exception:
        print(resp.text)
        return resp.text


