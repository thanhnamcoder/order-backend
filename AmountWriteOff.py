def get_amount_write_off(start_date, end_date, session_id):
    url = (
        "https://ss.circlek.com.vn/scmaster/a/inventoryVoucher/getDataByType?"
        f"page=1&rows=1000000&sidx=id&sord=desc&searchJson=%7B%22regionCd%22:%22%22,%22cityCd%22:%22%22,%22districtCd%22:%22%22,%22storeCd%22:%22%22,%22voucherNo%22:%22%22,%22voucherStartDate%22:%22{start_date}%22,%22voucherEndDate%22:%22{end_date}%22,%22itemInfo%22:%22%22,%22reviewSts%22:%22-1%22,%22voucherType%22:%22603%22,%22reason%22:%22%22%7D&_={int(__import__('time').time() * 1000)}"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
        "Connection": "keep-alive",
        "Referer": "https://ss.circlek.com.vn/scmaster/a/stockScrap",
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {
        "SESSION": session_id,
    }
    response = requests.get(url, headers=headers, cookies=cookies)
    if response.status_code != 200:
        print(f"[DEBUG] Status code: {response.status_code}")
        print(f"[DEBUG] Response text: {response.text}")
        return None
    try:
        return response.json()
    except Exception as e:
        print(f"[DEBUG] JSON decode error: {e}")
        print(f"[DEBUG] Response text: {response.text}")
        return None
