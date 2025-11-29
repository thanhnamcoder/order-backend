import os
import json
import time
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import RequestException
from loginCirclek import get_session_token
from login_utils import get_login_info


# ============================================================
# 🔹 API Layer: Xây dựng request tới Circle K API
# ============================================================
def build_headers(session_id: str) -> dict:
    return {
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/141.0.0.0 Safari/537.36"
        ),
        "accept": "application/json, text/javascript, */*; q=0.01",
        "x-requested-with": "XMLHttpRequest",
        "cookie": f"SESSION={session_id}",
    }


def build_inventory_params(store_cd: str, stock_date: str,
                           item_code: str = "", item_barcode: str = "",
                           page=1, rows=10) -> dict:
    """Tạo params JSON cho API Circle K"""
    search_json = {
        "storeCd": store_cd,
        "stockDate": stock_date,
        "itemCode": item_code,
        "itemBarcode": item_barcode,
        "depId": "",
        "pmaId": "",
        "categoryId": "",
        "omCode": "",
        "ofcCode": "",
        "subCategoryId": "",
        "vendorId": "",
    }
    return {
        "page": page,
        "rows": rows,
        "sidx": "id",
        "sord": "desc",
        "searchJson": json.dumps(search_json),
    }


def get_inventory(session_id: str, store_cd: str, stock_date: str,
                  item_code: str = "", item_barcode: str = "",
                  page=1, rows=10000000, retries=3, delay=2) -> dict:
    """Gọi API lấy tồn kho 1 store, có retry khi lỗi"""
    url = "https://ss.circlek.com.vn/scmaster/a/rtInventoryQuery/getInventory"
    headers = build_headers(session_id)
    params = build_inventory_params(store_cd, stock_date, item_code, item_barcode, page, rows)

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except RequestException as e:
            print(f"⚠️ [{store_cd}] Thử lại lần {attempt+1}/{retries} do lỗi: {e}")
            time.sleep(delay)
    raise Exception(f"❌ [{store_cd}] Lỗi sau {retries} lần thử.")


# ============================================================
# 🔹 FETCH Layer: Đa luồng xử lý nhiều store + item
# ============================================================
def fetch_one_task(session_id, store_cd, stock_date, value, mode, rows):
    """Lấy inventory cho 1 cặp (store, item_code/barcode)"""
    item_code = value if mode == "code" else ""
    item_barcode = value if mode == "barcode" else ""
    try:
        data = get_inventory(session_id, store_cd, stock_date, item_code, item_barcode, rows=rows)
        rows_data = data.get("rows", [])
        if not rows_data:
            return pd.DataFrame()

        df = pd.DataFrame(rows_data)
        df["storeCd"] = store_cd
        if mode != "all":
            df["queryType"] = mode
            df["queryValue"] = value
        return df

    except Exception as e:
        print(f"❌ [{store_cd}] Lỗi khi lấy dữ liệu ({value}): {e}")
        return pd.DataFrame()


def fetch_inventory_parallel(session_id, store_cd_list, stock_date,
                             item_codes=None, item_barcodes=None,
                             rows=10, max_workers=None):
    """Tải dữ liệu tồn kho song song"""
    start = time.time()
    results = []

    # Chọn chế độ
    if item_codes:
        mode = "code"
        items = item_codes
    elif item_barcodes:
        mode = "barcode"
        items = item_barcodes
    else:
        mode = "all"
        items = [None]

    # Tạo danh sách task (store x item)
    tasks = [(store, item) for store in store_cd_list for item in items]

    # Giới hạn luồng tối đa
    if max_workers is None:
        max_workers = min(len(tasks), os.cpu_count() * 2 or 10)

    print(f"\n🚀 Bắt đầu tải {len(tasks)} request với {max_workers} luồng...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_one_task, session_id, store, stock_date, item, mode, rows): (store, item)
            for store, item in tasks
        }

        for future in as_completed(futures):
            df = future.result()
            if not df.empty:
                results.append(df)

    if results:
        merged_df = pd.concat(results, ignore_index=True)
        duration = time.time() - start
        print(f"\n✅ Hoàn tất: {len(merged_df)} dòng từ {len(results)} request ({duration:.2f}s)")
        return merged_df

    print("\n⚠️ Không có dữ liệu hợp lệ.")
    return pd.DataFrame()


# ============================================================
# 🔹 EXPORT Layer: Lưu file Excel
# ============================================================
def export_to_excel(df: pd.DataFrame, folder="data", prefix="inventory"):
    if df.empty:
        print("\n⚠️ Không có dữ liệu để lưu.")
        return
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{prefix}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    df.to_excel(filename, index=False)
    print(f"\n✅ Đã lưu {len(df)} dòng vào: {filename}")


# ============================================================
# 🔹 MAIN
# ============================================================
def main():
    session_id = get_session_token()
    store_cd_group = get_login_info("store_cd_group")
    stock_date = "20251010"

    # ❗ Chọn 1 trong 2
    item_codes = None
    item_barcodes = "", "", "", ""

    df = fetch_inventory_parallel(
        session_id, store_cd_group, stock_date,
        item_codes=item_codes, item_barcodes=item_barcodes,
        rows=1000000
    )

    export_to_excel(df)


# ============================================================
# 🔹 Entry point
# ============================================================
if __name__ == "__main__":
    main()
