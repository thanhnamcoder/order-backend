import requests
import json
from bs4 import BeautifulSoup
import os, time, re, concurrent.futures
from datetime import datetime
import pandas as pd

# ========== CÁC HÀM EXPORT ==========

def export_dep_report(session_id, store_cd, start_date, end_date):
    url = "https://ss.circlek.com.vn/scmaster/a/classifiedSaleReport/export"
    payload = {
        "regionCd": "", "cityCd": "", "districtCd": "", "storeCd": store_cd,
        "am": "", "startDate": start_date, "endDate": end_date,
        "depCd": "", "categoryCd": "", "subCategoryCd": "",
        "pmaCd": "", "page": 1, "rows": 10
    }
    headers = {
        "accept": "*/*", "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "cookie": f"SESSION={session_id}",
        "referer": "https://ss.circlek.com.vn/scmaster/a/classifiedSaleReport",
        "user-agent": "Mozilla/5.0"
    }
    resp = requests.post(url, data={"searchJson": json.dumps(payload, ensure_ascii=False)}, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")
    tag = soup.find("input", id="expKey")
    return tag["value"] if tag else None


def export_sell_day_report(session_id, store_cd, start_date, end_date, include_service="20", type_date="1"):
    url = "https://ss.circlek.com.vn/scmaster/a/sellDayReport/export"
    payload = {
        "regionCd": "", "cityCd": "", "districtCd": "", "storeCd": store_cd,
        "am": "", "effectiveStartDate": start_date, "effectiveEndDate": end_date,
        "page": 1, "rows": 10, "includeService": include_service, "typeDate": type_date
    }
    headers = {
        "accept": "*/*", "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "cookie": f"SESSION={session_id}",
        "referer": "https://ss.circlek.com.vn/scmaster/a/sellDayReport",
        "user-agent": "Mozilla/5.0"
    }
    resp = requests.post(url, data={"searchJson": json.dumps(payload, ensure_ascii=False)}, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")
    tag = soup.find("input", id="expKey")
    return tag["value"] if tag else None


def export_sell_item_report(session_id, store_cd, start_date, end_date, department_cd=None, category_cd=None, subCategory_cd=None, barcode=None, articleName=None):
    import urllib.parse
    url = "https://ss.circlek.com.vn/scmaster/a/GoodsSaleReport/export"
    payload = {
        "regionCd": "", "cityCd": "", "districtCd": "", "storeCd": store_cd,
        "am": "", "depCd": "", "pmaCd": department_cd, "categoryCd": category_cd,
        "subCategoryCd": subCategory_cd, "startDate": start_date, "endDate": end_date,
        "barcode": barcode, "articleName": articleName, "page": 1, "rows": 10
    }
    full_url = f"{url}?{urllib.parse.urlencode({'searchJson': json.dumps(payload, ensure_ascii=False)})}"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "cookie": f"SESSION={session_id}",
        "user-agent": "Mozilla/5.0"
    }
    resp = requests.get(full_url, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")
    tag = soup.find("input", id="expKey")
    return tag["value"] if tag else None


# ========== CHECK + DOWNLOAD ==========

def exp_check(session_id, exp_key, timeout=99):
    """Kiểm tra export có sẵn sàng trong tối đa `timeout` giây"""
    url = "https://ss.circlek.com.vn/scmaster/a/expcheck"
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "cookie": f"SESSION={session_id}",
        "x-requested-with": "XMLHttpRequest",
        "user-agent": "Mozilla/5.0"
    }
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.post(url, data={"key": exp_key}, headers=headers, timeout=10)
            data = resp.json()
            if data.get("status") == 2 and "filename" in data:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def download_exported_file(exp_key_value, session_id, folder_path=None, filename=None):
    import os, re, requests

    download_url = f"https://ss.circlek.com.vn/scmaster/a/export/{exp_key_value}"
    headers = {"cookie": f"SESSION={session_id}"}
    response = requests.get(download_url, headers=headers)

    if response.status_code == 200:
        # 🔍 Lấy tên từ server
        server_filename = None
        content_disposition = response.headers.get("content-disposition", "")
        match = re.search(r'filename="?([^"]+)"?', content_disposition)
        if match:
            server_filename = match.group(1)
        
        # Nếu server_filename có đuôi .xlsx thì bỏ đuôi đó để nối gọn hơn
        if server_filename and server_filename.lower().endswith(".xlsx"):
            server_filename = server_filename[:-5]

        # ✅ Nếu có filename truyền vào → ghép cả 2
        if filename:
            final_name = f"{filename}__{server_filename or exp_key_value}.xlsx"
        else:
            final_name = f"{server_filename or exp_key_value}.xlsx"

        save_path = os.path.join(folder_path, final_name)

        with open(save_path, "wb") as f:
            f.write(response.content)

        return save_path

    else:
        print(f"⚠️ Lỗi tải file (status {response.status_code})")
        return None



# ========== GỘP FILE NHANH BẰNG PANDAS + SONG SONG ==========

def merge_excel_fast_parallel(saved_files, output_path, header_row=2, max_workers=20):
    """Gộp nhanh các file Excel bằng pandas (đa luồng đọc song song)"""
    t0 = time.time()

    def read_file(path):
        try:
            df = pd.read_excel(path, header=header_row, engine="openpyxl")
            return df
        except Exception as e:
            print(f"❌ Lỗi đọc {path}: {e}")
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        dfs = list(ex.map(read_file, saved_files))

    dfs = [d for d in dfs if d is not None]
    if not dfs:
        print("⚠️ Không có file hợp lệ để gộp!")
        return

    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df.to_excel(output_path, index=False, engine="openpyxl")

    print(f"✅ Đã gộp {len(saved_files)} file ({len(merged_df)} dòng)")
    print(f"⚡ Thời gian gộp: {round(time.time() - t0, 2)}s")


# ========== QUẢN LÝ CHÍNH ==========

def group_craw_data(
    session_id, store_cd_group, start_date, end_date, type_report,
    folder_path, department_cd=None, category_cd=None,
    subCategory_cd=None, barcode=None, articleName=None,
    merge_files=True,
    format_export_sell_item_report=False,
    format_export_dep_report=False,
    format_export_sell_day_report=False
):
    import os, re, concurrent.futures
    from datetime import datetime

    print(f"\n🕒 {datetime.now().strftime('%H:%M:%S')} | BẮT ĐẦU {type_report}")

    # 🔹 Tự động xác định thư mục con theo loại report
    if type_report == "export_sell_item_report":
        folder_path = os.path.join(folder_path, "Item Sales Data")
    elif type_report == "export_dep_report":
        folder_path = os.path.join(folder_path, "Department Data")
    elif type_report == "export_sell_day_report":
        folder_path = os.path.join(folder_path, "Sales Data")
    else:
        folder_path = os.path.join(folder_path, "Other Reports")

    os.makedirs(folder_path, exist_ok=True)  # đảm bảo thư mục tồn tại

    exp_key_map = {}

    # 1️⃣ Lấy exp_key tuần tự
    for store_cd in store_cd_group:
        try:
            if type_report == "export_sell_item_report":
                exp_key = export_sell_item_report(
                    session_id, store_cd, start_date, end_date,
                    department_cd, category_cd, subCategory_cd,
                    barcode, articleName
                )
            elif type_report == "export_sell_day_report":
                exp_key = export_sell_day_report(session_id, store_cd, start_date, end_date)
            elif type_report == "export_dep_report":
                exp_key = export_dep_report(session_id, store_cd, start_date, end_date)
            else:
                exp_key = None

            print(f"→ {store_cd}: exp_key = {exp_key}")
            exp_key_map[store_cd] = exp_key
        except Exception as e:
            print(f"❌ {store_cd}: lỗi lấy exp_key ({e})")

    # 2️⃣ Đa luồng exp_check + download
    def process_download(store_cd, exp_key):
        if not exp_key:
            return f"⚠️ {store_cd}: Không có exp_key"
        if exp_check(session_id, exp_key):
            save_path = download_exported_file(exp_key, session_id, folder_path, store_cd)
            return f"✅ {store_cd}: Tải thành công {save_path}" if save_path else f"⚠️ {store_cd}: Không tải được file"
        else:
            return f"⚠️ {store_cd}: Hết hạn chờ export"

    saved_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(20, len(store_cd_group))) as executor:
        futures = {executor.submit(process_download, s, k): s for s, k in exp_key_map.items()}
        for fut in concurrent.futures.as_completed(futures):
            result = fut.result()
            print(result)
            if "Tải thành công" in result:
                path_match = re.search(r" (C:.+\.xlsx)", result)
                if path_match:
                    saved_files.append(path_match.group(1))

    # 3️⃣ Gộp file nhanh + format nếu cần
    if merge_files and saved_files:
        try:
            merged_filename = os.path.join(
                folder_path, f"GROUP_MS.MAIPHUONG_{type_report}_{start_date}_{end_date}.xlsx"
            )
            merge_excel_fast_parallel(saved_files, merged_filename)

            # 🧩 Gọi format tương ứng
            if type_report == "export_sell_item_report" and format_export_sell_item_report:
                format_sell_item_report(merged_filename)

            elif type_report == "export_dep_report" and format_export_dep_report:
                format_dep_report(merged_filename)

            elif type_report == "export_sell_day_report" and format_export_sell_day_report:
                format_sell_day_report(merged_filename)

        except Exception as e:
            print(f"❌ Lỗi khi gộp/format file: {e}")

    print(f"🏁 {datetime.now().strftime('%H:%M:%S')} | HOÀN THÀNH {type_report}")


def format_sell_item_report(filepath):
    print(f"🎨 Format file SELL ITEM REPORT: {filepath}")
    import pandas as pd

    # Đọc file Excel
    df = pd.read_excel(filepath)

    # 1️⃣ Sort theo "Store No."
    if "Store No." in df.columns:
        df["Store No."] = df["Store No."].astype(str)
        df = df.sort_values(by="Store No.", ascending=True)
        print("✅ Đã sort theo 'Store No.' (A → Z)")
    else:
        print("⚠️ Không tìm thấy cột 'Store No.' để sort")

    # 2️⃣ Xóa các dòng chứa "Total item:" trong cột Department
    if "Department" in df.columns:
        before_count = len(df)
        # Remove rows that contain 'Total item' (partial match)
        df = df[~df["Department"].astype(str).str.contains("Total item", case=False, na=False)]
        # Also remove rows where Department equals '19 Services' (exact match after strip)
        df = df[df["Department"].astype(str).str.strip() != "19 Services"]
        after_count = len(df)
        removed = before_count - after_count
        print(f"🧹 Đã xoá {removed} dòng có 'Total item:' hoặc '19 Services' trong cột Department")
    else:
        print("⚠️ Không tìm thấy cột 'Department' để lọc")

    # 3️⃣ Xóa cột "NO." nếu tồn tại
    if "NO." in df.columns:
        df = df.drop(columns=["NO."])
        print("🗑️ Đã xoá cột 'NO.'")
    else:
        print("⚠️ Không có cột 'NO.' để xoá")

    # 4️⃣ Ghi đè lại file gốc
    df.to_excel(filepath, index=False)
    print(f"💾 Đã ghi đè file sau khi format: {filepath}")



def format_dep_report(filepath):
    import pandas as pd

    print(f"🎨 Format file DEP REPORT: {filepath}")

    # Đọc file Excel
    df = pd.read_excel(filepath)

    # 🧹 Xóa cột "NO." nếu có
    if "NO" in df.columns:
        df = df.drop(columns=["NO"])
        print("🧾 Đã xóa cột 'NO'")

    # 🔽 Sort theo 'Store No.' nếu có
    if "Store No." in df.columns:
        df = df.sort_values(by="Store No.", ascending=True)
        print("✅ Đã sort theo 'Store No.' (A → Z)")

    # ❌ Xóa các dòng có Department = "19 Services"
    if "Department" in df.columns:
        before = len(df)
        df = df[df["Department"].astype(str).str.strip() != "19 Services"]
        after = len(df)
        print(f"🚮 Đã xóa {before - after} dòng có 'Department' = '19 Services'")

    # 💾 Ghi đè lại file
    df.to_excel(filepath, index=False)
    print("💾 Đã lưu file sau khi format xong.")

def format_sell_day_report(filepath):
    import pandas as pd

    print(f"📅 Format file SELL DAY REPORT: {filepath}")

    # Đọc dữ liệu
    df = pd.read_excel(filepath)

    # 🧹 Xóa cột "NO." nếu có
    if "NO." in df.columns:
        df = df.drop(columns=["NO."])
        print("🧾 Đã xóa cột 'NO.'")

    # 1️⃣ Chuẩn hóa dữ liệu Store No.
    if "Store No." not in df.columns:
        print("⚠️ Không tìm thấy cột 'Store No.'")
        return

    # Lưu cột gốc để tham chiếu
    df["__Store_Group__"] = df["Store No."].ffill()  # Lan giá trị Store No. xuống các dòng con

    # 2️⃣ Sort theo nhóm Store No. (và giữ nguyên thứ tự trong nhóm)
    df["_sort_order"] = df.index  # giữ vị trí gốc
    df = df.sort_values(by=["__Store_Group__", "_sort_order"], ascending=[True, True])
    df = df.drop(columns=["_sort_order", "__Store_Group__"])

    # 3️⃣ Format cột Date nếu có
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # 4️⃣ Ghi lại file
    df.to_excel(filepath, index=False)
    print("✅ Đã sort theo 'Store No.' (A → Z) và giữ nguyên nhóm dữ liệu gốc.")



def format_sell_single_item_report(filepath):
    print(f"🎨 Format file SELL ITEM REPORT: {filepath}")

    # 1️⃣ Đọc Excel, bỏ 2 dòng đầu, lấy dòng 3 làm header
    df = pd.read_excel(filepath, header=2)
    print("✅ Đã lấy dòng 3 làm header (bỏ 2 dòng đầu)")

    # 2️⃣ Danh sách các cột cần xoá
    cols_to_remove = [
        "NO.",
        "Store No.",
        "Store Name",
        # "Sale Date",
        "Top Department",
        "Selling Price",
        "Area Manager ID",
        "Area Manager Name",
    ]

    # 3️⃣ Xoá các cột tồn tại trong danh sách
    existing_cols = [c for c in cols_to_remove if c in df.columns]
    if existing_cols:
        df = df.drop(columns=existing_cols)
        print(f"🗑️ Đã xoá các cột: {', '.join(existing_cols)}")

    # 4️⃣ Xóa các dòng có giá trị "19 Services" trong cột Department
    if "Department" in df.columns:
        before = len(df)
        df = df[~df["Department"].astype(str).str.contains("19 Services|Total item:", case=False, na=False)]
        removed = before - len(df)
        print(f"🧹 Đã xoá {removed} dòng có '19 Services' trong cột Department")

    # 5️⃣ Ghi đè lại file gốc
    df.to_excel(filepath, index=False)
    print(f"💾 Đã ghi đè file sau khi format: {filepath}")

    # 6️⃣ Trả về JSON (convert DataFrame thành list of dict)
    data_json = df.to_dict(orient="records")
    return data_json


def item_sell_by_store(start_date, end_date, department_cd, category_cd, subCategory_cd):
    from loginCirclek import get_session_token
    from login_utils import get_login_info
    BASE_PATH = r'C:\Users\SG0xxx-Tablet\Documents\SM\TOOL BCS\Order\order-backend'
    ITEM_FOLDER = os.path.join(BASE_PATH, 'Data', 'Item')

    # Tạo thư mục nếu chưa có
    os.makedirs(ITEM_FOLDER, exist_ok=True)

    session_id = get_session_token()
    store_cd = get_login_info("store_cd")
    exp_key = export_sell_item_report(session_id, store_cd, start_date, end_date, department_cd, category_cd=category_cd, subCategory_cd=subCategory_cd)
    if exp_check(session_id, exp_key):
        print(exp_key)

        save_path = download_exported_file(exp_key, session_id, ITEM_FOLDER, store_cd)

        # 🔧 Format Excel và lấy JSON
        data_json = format_sell_single_item_report(save_path)

        # # 💾 Ghi JSON ra file
        # json_filename = f"{store_cd}_SELL_ITEM_{start_date}_{end_date}.json"
        # json_path = os.path.join(ITEM_FOLDER, json_filename)
        # with open(json_path, "w", encoding="utf-8") as f:
        #     json.dump(data_json, f, ensure_ascii=False, indent=2)

        # print(f"✅ Đã lưu file JSON: {json_path}")

        # print(data_json)
        return data_json
    else:
        print("❌ Không thể export file SELL ITEM REPORT")
        return []
# print(item_sell_by_store("20251031", "20251031", "", "", ""))
# from loginCirclek import get_session_token
# from login_utils import get_login_info
# BASE_PATH = r'C:\Users\SG0xxx-Tablet\Documents\SM\TOOL BCS\Order\order-backend'
# ITEM_FOLDER = os.path.join(BASE_PATH, 'Data', 'Item')
# session_id = get_session_token()
# store_cd_group = get_login_info("store_cd_group")
# store_cd = get_login_info("store_cd")
# start_date = "20251101"
# end_date = "20251127"
# group_craw_data(
#     session_id=session_id,
#     store_cd_group=store_cd_group,
#     start_date=start_date,
#     end_date=end_date,
#     type_report="export_sell_day_report",
#     folder_path=ITEM_FOLDER,
#     department_cd="",      # tùy theo cấu trúc hệ thống
#     category_cd=None,
#     subCategory_cd=None,
#     barcode="",
#     articleName="",
#     merge_files=True,  # Đặt False nếu không muốn gộp file
#     format_export_sell_item_report=True,
#     format_export_dep_report=True,
#     format_export_sell_day_report=True
# )