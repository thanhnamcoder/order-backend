import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from loginCirclek import get_session_token
from login_utils import get_login_info


def get_write_off_data(session_id, store_cd, item_code):
    """
    Gửi request lấy thông tin 1 itemCode.
    Server chỉ nhận 1 code mỗi lần, nên hàm này được dùng trong đa luồng.
    """
    url = "https://ss.circlek.com.vn/scmaster/a/inventoryVoucher/getItemWithChild"
    payload = {
        "itemCode": item_code,
        "storeCd": store_cd
    }

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "cookie": f"SESSION={session_id}",
        "origin": "https://ss.circlek.com.vn",
        "referer": "https://ss.circlek.com.vn/scmaster/a/stockScrap/edit?flag=add",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    try:
        resp = requests.post(url, data=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Dữ liệu thực nằm trong key "o"
        if isinstance(data, dict) and "o" in data.get(item_code, {}):
            item = data[item_code]["o"]
        elif isinstance(data, dict) and "o" in data:
            item = data["o"]
        else:
            # fallback: nếu cấu trúc khác
            item = data

        return {
            "itemCode": item.get("itemCode"),
            "barcode": item.get("barcode"),
            "itemName": item.get("itemName"),
            "baseOrderPrice": item.get("baseOrderPrice")
        }

    except Exception as e:
        return {
            "itemCode": item_code,
            "error": str(e)
        }


def get_multiple_price_cost(item_codes):
    """
    Chạy đa luồng để lấy dữ liệu nhiều itemCode cùng lúc.
    """
    session_id = get_session_token()
    store_cd = get_login_info("store_cd")
    results = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(get_write_off_data, session_id, store_cd, code): code for code in item_codes}
        for future in as_completed(futures):
            results.append(future.result())

    return json.dumps(results, indent=2, ensure_ascii=False)


