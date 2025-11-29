import requests
from loginCirclek import get_session_token
from collections import defaultdict
from login_utils import get_login_info
from datetime import date

def get_write_off_data(store_cd, write_off_start_date, write_off_end_date, session_id):
    url = "https://ss.circlek.com.vn/scmaster/a/writeOff/getData"
    import json as _json
    payload = {
        "regionCd": "",
        "cityCd": "",
        "districtCd": "",
        "storeCd": store_cd,
        "writeOffStartDate": write_off_start_date,
        "writeOffEndDate": write_off_end_date,
        "adjustReason": "",
        "barcode": "" , 
        "depCd": "",
        "am": "",
        "pmaCd": "",
        "subCategoryCd": "",
        "categoryCd": "",
        "articleName": "",
        "page": 1,
        "rows": 1000000
    }
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "cookie": f"SESSION={session_id}",
        "origin": "https://ss.circlek.com.vn",
        "referer": "https://ss.circlek.com.vn/scmaster/a/writeOff",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }
    data = {"SearchJson": _json.dumps(payload, ensure_ascii=False)}
    response = requests.post(url, data=data, headers=headers)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        print("Status code:", response.status_code)
        print("Response text:", response.text)
        raise
    # print(response.json())
    return response.json()

def formart_data(data):
    
    # Defensive: handle None for data, data['o'], or data['o']['data']
    rows = []
    if data and isinstance(data, dict):
        o = data.get("o")
        if o and isinstance(o, dict):
            rows = o.get("data")
            if rows is None:
                rows = []
    if not isinstance(rows, list):
        rows = []

    totals = defaultdict(float)  # lưu tổng qty theo articleId

    for row in rows:
        if not isinstance(row, dict):
            continue
        article_id = row.get("articleId")
        qty = row.get("writeOffQty", 0) or 0
        totals[article_id] += qty

    # trả ra list hoặc dict tùy bạn cần
    result = [{"articleId": k, "totalWriteOffQty": v} for k, v in totals.items()]
    return result

def get_quantity_item_write_off():
    store_cd = get_login_info().get("store_cd")

    # Lấy ngày hôm nay
    today = date.today()

    # start_date: ngày 1 của tháng hiện tại
    start_date = today.replace(day=1).strftime("%Y%m%d")

    # end_date: hôm nay
    end_date = today.strftime("%Y%m%d")

    session_id = get_session_token()

    data = get_write_off_data(store_cd, start_date, end_date, session_id)
    result = formart_data(data)
    return result

    # from login_utils import get_login_info
    # from loginCirclek import get_session_token
    # import json
    # session_id = get_session_token()
    # store_cd = get_login_info("store_cd")
    # start_date = "20251001"
    # end_date = "20251018"
    # # ==== 2. Gọi API hoặc hàm lấy dữ liệu ====
    # data = get_write_off_data(store_cd, start_date, end_date, session_id)

    # # ==== 3. Lưu ra file JSON ====
    # output_filename = f"write_off_{store_cd}_{start_date}_{end_date}.json"

    # with open(output_filename, "w", encoding="utf-8") as f:
    #     json.dump(data, f, ensure_ascii=False, indent=2)

    # print(f"✅ Dữ liệu đã được lưu vào file: {output_filename}")