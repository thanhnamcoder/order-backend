import os
import pandas as pd
import json
from loginCirclek import get_session_token
from ExportFile import download_exported_file, export_sell_item_report, exp_check
from login_utils import get_login_info
# ===========================
# Cấu hình chung
# ===========================
BASE_PATH = r'C:\Users\SG0xxx-Tablet\Documents\SM\TOOL BCS\Order\order-backend'
ITEM_FOLDER = os.path.join(BASE_PATH, 'Data', 'Item')
STORE_CD = get_login_info("store_cd")
os.makedirs(ITEM_FOLDER, exist_ok=True)

# ===========================
# Hàm tải và xử lý file Excel
# ===========================
def clean_excel(file_path, period, startDate, endDate):
    df_raw = pd.read_excel(file_path, header=None, engine="openpyxl")
    # Xóa 2 dòng đầu (header gốc)
    df_raw = df_raw.iloc[2:].reset_index(drop=True)

    # Dòng đầu tiên sau khi xóa là header
    header = df_raw.iloc[0]
    # Các dòng tiếp theo là data
    df_data = df_raw.iloc[1:].reset_index(drop=True)
    df_data.columns = header

    # Xóa các cột thừa dựa vào header
    cols_to_drop = ["Store Name", "Area Manager Name", "Store No.", "NO.", "Top Department", "Selling Price", "Area Manager ID"]
    df_data = df_data.drop(columns=[c for c in cols_to_drop if c in df_data.columns], errors="ignore")

    # Thêm kỳ
    df_data["period"] = period
    df_data["startDate"] = startDate
    df_data["endDate"] = endDate

    return df_data


def download_and_clean(start, end, filename):
    session_id = get_session_token()
    """Xuất dữ liệu, tải về, clean và xóa file gốc."""
    # Đặt tên file theo kỳ
    file_tag = f"{filename}_{start}-{end}"
    exp_key = export_sell_item_report(session_id, STORE_CD, start, end)
    if exp_check(session_id, exp_key):

        file_path = download_exported_file(
        exp_key,
        session_id,
        folder_path=ITEM_FOLDER,   # 👈 tham số đúng là folder_path
        filename=file_tag,
    )

    # Đọc và clean
    df = clean_excel(file_path, filename, start, end)

    # Không xóa file gốc nữa
    return df

def start_comparison_sales(startLast, endLast, startThis, endThis):
    # --- Tải và clean ---
    df_this = download_and_clean(startThis, endThis, "this")
    df_last = download_and_clean(startLast, endLast, "last")

    # --- Gộp ---
    df_all = pd.concat([df_this, df_last], ignore_index=True)
    df_all = df_all.drop(columns=["startDate", "endDate"], errors="ignore")
    df_all.to_excel(os.path.join(ITEM_FOLDER, "all_data.xlsx"), index=False)
    # --- Summary ---


# start_comparison_sales("20250901", "20250901", "20250921", "20251021")