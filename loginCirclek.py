import requests
from login_utils import get_login_info

LOGIN_URL = "https://ss.circlek.com.vn/scmaster/a/dologin"
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://ss.circlek.com.vn",
    "referer": "https://ss.circlek.com.vn/scmaster/a/login",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}

def get_session_token(user=None, password=None):
    if user is None or password is None:
        user, password = get_login_info(["user", "password"])
    if not user or not password:
        print("File user_login.json chưa có đủ thông tin đăng nhập. Vui lòng nhập từ giao diện.")
        return None
    LOGIN_URL = "https://ss.circlek.com.vn/scmaster/a/dologin"
    HEADERS = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://ss.circlek.com.vn",
        "referer": "https://ss.circlek.com.vn/scmaster/a/login",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }
    payload = {
        "userid": user,
        "password": password
    }
    with requests.Session() as s:
        resp = s.post(LOGIN_URL, headers=HEADERS, data=payload, allow_redirects=False)
        session_cookie = s.cookies.get_dict().get("SESSION")
        if session_cookie:
            print(f"Đăng nhập thành công, SESSION token: {session_cookie}")
            return session_cookie
        else:
            print("Không lấy được SESSION token. Kiểm tra lại thông tin đăng nhập hoặc headers.")
            return None

def get_out_store_list(store_cd=None, zo_cds=None):
    """
    Lấy danh sách Out Store từ API Circle K (đã đăng nhập).

    Nếu truyền `store_cd` (ví dụ: 'DC9991') thì sẽ trả về dict chỉ chứa `k` và `v` của store khớp.
    Nếu không truyền `store_cd`, hành vi như cũ sẽ trả về toàn bộ danh sách (list).
    """
    session_id = get_session_token()
    if not session_id:
        print("❌ Không có session_id, vui lòng đăng nhập trước.")
        return []

    base_url = "https://ss.circlek.com.vn/scmaster/a/inventoryVoucher/getOutStoreList"
    # zo_cds can be a single string like 'S00001' or a list of zo codes.
    if zo_cds is None:
        zo_cds = ["S00001", "N00001"]
    elif isinstance(zo_cds, str):
        zo_cds = [zo_cds]

    # common params; we'll set zoCd per-request
    base_params = {
        "v": "",
        "_": "1762249007903"
    }

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Referer": "https://ss.circlek.com.vn/scmaster/",
        "X-Requested-With": "XMLHttpRequest",
    }

    # ⚠️ CHỈNH LẠI cookie: SESSION (không phải JSESSIONID)
    cookies = {"SESSION": session_id}

    # We'll call the endpoint for each zoCd and aggregate results.
    stores = []
    seen_keys = set()
    for zo in zo_cds:
        params = dict(base_params)
        params["zoCd"] = zo
        try:
            response = requests.get(base_url, params=params, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            # Warn and continue with next zoCd
            print(f"❌ Lỗi khi lấy danh sách Out Store cho zoCd={zo}:", e)
            try:
                print("🔎 Response text:", response.text[:300])
            except Exception:
                pass
            continue

        # parse JSON for this zo
        local_stores = []
        if isinstance(data, dict) and "data" in data:
            local_stores = data["data"]
        elif isinstance(data, list):
            local_stores = data
        else:
            print(f"⚠️ Dữ liệu không đúng định dạng cho zoCd={zo}:", data)
            continue

        # merge while avoiding duplicates by 'k'
        for s in local_stores:
            try:
                key = s.get("k")
            except Exception:
                key = None
            if key and key not in seen_keys:
                seen_keys.add(key)
                stores.append(s)

    # Nếu yêu cầu filter theo store_cd, trả về đúng k và v của store đó (hoặc None nếu không tìm thấy)
    if store_cd:
        for s in stores:
            try:
                if s.get("k") == store_cd:
                    return {"k": s.get("k"), "v": s.get("v")}
            except Exception:
                # nếu record không theo định dạng mong đợi, bỏ qua
                continue
        # không tìm thấy store_cd
        return None

    # Trường hợp không truyền store_cd: trả về danh sách đầy đủ như trước
    return stores
