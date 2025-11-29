import requests
from loginCirclek import get_session_token

def get_quantity_item_sale(store_cd, from_business_date, to_business_date, session_id, dep_cd="", sub_category_cd=""):
    url = "https://ss.circlek.com.vn/scmaster/a/GoodsSaleReport/search"
    import json as _json
    payload = {
        "regionCd": "",
        "cityCd": "",
        "districtCd": "",
        "storeCd": store_cd,
        "am": "",
        "depCd": "",
        "pmaCd": dep_cd,
        "categoryCd": "",
        "subCategoryCd": sub_category_cd,
        "startDate": from_business_date,
        "endDate": to_business_date,
        # "barcode": item_code,
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
        "referer": "https://ss.circlek.com.vn/scmaster/a/GoodsSaleReport",
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
