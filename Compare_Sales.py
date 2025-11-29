import os
import pandas as pd
import json
import io
from loginCirclek import get_session_token
from ExportFile import download_exported_file, export_sell_day_report, exp_check
from login_utils import get_login_info
# ===========================
# Cấu hình chung
# ===========================
BASE_PATH = r'C:\Users\SG0xxx-Tablet\Documents\SM\TOOL BCS\Order\order-backend'
SALES_FOLDER = os.path.join(BASE_PATH, 'Data', 'Sales')
os.makedirs(SALES_FOLDER, exist_ok=True)

# Biến điều khiển: True = xử lý trên RAM, False = xử lý file vật lý
USE_MEMORY = False

# ===========================
# Hàm tải và xử lý file Excel
# ===========================
def clean_excel(file_input, period, startDate, endDate):
    # file_input: bytes (Excel file in memory) hoặc đường dẫn file
    if USE_MEMORY:
        df_raw = pd.read_excel(io.BytesIO(file_input), header=None, engine="openpyxl")
    else:
        df_raw = pd.read_excel(file_input, header=None, engine="openpyxl")
    df_raw = df_raw.iloc[2:].reset_index(drop=True)

    # Header
    header = df_raw.iloc[0]
    df_value = df_raw.iloc[1::2].reset_index(drop=True)   # Amount
    df_count = df_raw.iloc[2::2].reset_index(drop=True)   # Customer

    df_value.columns = header
    df_count.columns = header

    # Loại bỏ cột thừa
    cols_to_drop = ["Store Name", "Area Manager Name", "Store No.", "NO."]
    df_value = df_value.drop(columns=[c for c in df_value.columns if c in cols_to_drop], errors="ignore")
    df_count = df_count.drop(columns=[c for c in df_count.columns if c in cols_to_drop], errors="ignore")

    # Ghép 2 bảng theo Date
    df_merged = df_value.copy()
    for col in df_count.columns:
        if col not in ["Date", "Total Amt", "Customer Count"]:
            df_merged[f"CC-{col}"] = df_count[col]

    # Thêm kỳ
    df_merged["period"] = period
    df_merged["startDate"] = startDate
    df_merged["endDate"] = endDate

    return df_merged


def download_and_clean(start, end, filename):
    store_cd = get_login_info("store_cd")
    session_id = get_session_token()
    """Xuất dữ liệu, tải về, clean (RAM hoặc file)."""
    # Đặt tên file theo kỳ
    file_tag = f"{filename}_{start}-{end}"
    exp_key = export_sell_day_report(session_id, store_cd, start, end)
    if exp_check(session_id, exp_key):

        file_path = download_exported_file(
            exp_key,
            session_id,
            folder_path=SALES_FOLDER,
            filename=file_tag,
        )
    if USE_MEMORY:
        with open(file_path, "rb") as f:
            file_content = f.read()
        try:
            os.remove(file_path)
        except Exception:
            pass
        df = clean_excel(file_content, filename, start, end)
    else:
        df = clean_excel(file_path, filename, start, end)
    return df

# ===========================
# Hàm main
# ===========================
def make_summary(df_all):
    import numpy as np

    # ===========================
    # By Shift
    # ===========================
    sales_cols = ["Shift1", "Shift2", "Shift3"]
    cc_cols = [f"CC-{s}" for s in sales_cols]

    df_sales = df_all.melt(
        id_vars=["period"],
        value_vars=sales_cols,
        var_name="Shift",
        value_name="Sales"
    )
    df_cc = df_all.melt(
        id_vars=["period"],
        value_vars=cc_cols,
        var_name="Shift",
        value_name="CC"
    )
    df_cc["Shift"] = df_cc["Shift"].str.replace("CC-", "")

    df_long = pd.merge(df_sales, df_cc, on=["period", "Shift"], how="inner")

    df_pivot = df_long.groupby(["Shift", "period"]).mean().reset_index()
    df_pivot = df_pivot.pivot(index="Shift", columns="period", values=["Sales", "CC"])
    df_pivot.columns = [f"{metric}-{period}" for metric, period in df_pivot.columns]
    df_pivot = df_pivot.reset_index()

    df_pivot["AT-this"] = df_pivot["Sales-this"] / df_pivot["CC-this"]
    df_pivot["AT-last"] = df_pivot["Sales-last"] / df_pivot["CC-last"]

    for metric in ["Sales", "CC", "AT"]:
        df_pivot[f"{metric}-diff"] = df_pivot[f"{metric}-this"] - df_pivot[f"{metric}-last"]
        df_pivot[f"{metric}-pct"] = df_pivot[f"{metric}-diff"] / df_pivot[f"{metric}-last"]

    # ===========================
    # By Hour
    # ===========================
    hour_cols = [
        "6h-8h", "8h-10h", "10h-12h", "12h-14h",
        "14h-16h", "16h-18h", "18h-20h", "20h-22h",
        "22h-24h", "0h-2h", "2h-4h", "4h-6h"
    ]

    df_sales_hour = df_all.melt(
        id_vars=["period"],
        value_vars=hour_cols,
        var_name="Hour",
        value_name="Sales"
    )
    df_cc_hour = df_all.melt(
        id_vars=["period"],
        value_vars=[f"CC-{h}" for h in hour_cols],
        var_name="Hour",
        value_name="CC"
    )
    df_cc_hour["Hour"] = df_cc_hour["Hour"].str.replace("CC-", "")

    df_long_hour = pd.merge(df_sales_hour, df_cc_hour, on=["period", "Hour"], how="inner")

    df_pivot_hour = df_long_hour.groupby(["Hour", "period"]).mean().reset_index()
    df_pivot_hour = df_pivot_hour.pivot(index="Hour", columns="period", values=["Sales", "CC"])
    df_pivot_hour.columns = [f"{metric}-{period}" for metric, period in df_pivot_hour.columns]
    df_pivot_hour = df_pivot_hour.reset_index()

    df_pivot_hour["AT-this"] = df_pivot_hour["Sales-this"] / df_pivot_hour["CC-this"]
    df_pivot_hour["AT-last"] = df_pivot_hour["Sales-last"] / df_pivot_hour["CC-last"]

    for metric in ["Sales", "CC", "AT"]:
        df_pivot_hour[f"{metric}-diff"] = df_pivot_hour[f"{metric}-this"] - df_pivot_hour[f"{metric}-last"]
        df_pivot_hour[f"{metric}-pct"] = df_pivot_hour[f"{metric}-diff"] / df_pivot_hour[f"{metric}-last"]

    # ===========================
    # Build JSON result
    # ===========================
    result = {}

    # Shift
    for _, row in df_pivot.iterrows():
        shift = row["Shift"]
        result[shift] = {
            "Sales": {
                "this": row["Sales-this"],
                "last": row["Sales-last"],
                "diff": row["Sales-diff"],
                "pct": row["Sales-pct"],
            },
            "CC": {
                "this": row["CC-this"],
                "last": row["CC-last"],
                "diff": row["CC-diff"],
                "pct": row["CC-pct"],
            },
            "AT": {
                "this": row["AT-this"],
                "last": row["AT-last"],
                "diff": row["AT-diff"],
                "pct": row["AT-pct"],
            },
        }

    # Hour
    for _, row in df_pivot_hour.iterrows():
        hour = row["Hour"]
        result[hour] = {
            "Sales": {
                "this": row["Sales-this"],
                "last": row["Sales-last"],
                "diff": row["Sales-diff"],
                "pct": row["Sales-pct"],
            },
            "CC": {
                "this": row["CC-this"],
                "last": row["CC-last"],
                "diff": row["CC-diff"],
                "pct": row["CC-pct"],
            },
            "AT": {
                "this": row["AT-this"],
                "last": row["AT-last"],
                "diff": row["AT-diff"],
                "pct": row["AT-pct"],
            },
        }

    # ===========================
    # Summary (tổng cộng all shift)
    # ===========================
    summary = {}
    for metric in ["Sales", "CC", "AT"]:
        this_val = (
            df_pivot["Sales-this"].sum() / df_pivot["CC-this"].sum()
            if metric == "AT"
            else df_pivot[f"{metric}-this"].sum()
        )
        last_val = (
            df_pivot["Sales-last"].sum() / df_pivot["CC-last"].sum()
            if metric == "AT"
            else df_pivot[f"{metric}-last"].sum()
        )
        diff = this_val - last_val
        pct = diff / last_val if last_val else None
        summary[f"{metric}-this"] = this_val
        summary[f"{metric}-last"] = last_val
        summary[f"{metric}-diff"] = diff
        summary[f"{metric}-pct"] = pct

    result["Summary"] = {
        "Sales": {
            "this": summary["Sales-this"],
            "last": summary["Sales-last"],
            "diff": summary["Sales-diff"],
            "pct": summary["Sales-pct"],
        },
        "CC": {
            "this": summary["CC-this"],
            "last": summary["CC-last"],
            "diff": summary["CC-diff"],
            "pct": summary["CC-pct"],
        },
        "AT": {
            "this": summary["AT-this"],
            "last": summary["AT-last"],
            "diff": summary["AT-diff"],
            "pct": summary["AT-pct"],
        },
    }

    # ===========================
    # Convert NaN / inf → None
    # ===========================
    def clean_json_values(obj):
        if isinstance(obj, dict):
            return {k: clean_json_values(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_json_values(v) for v in obj]
        elif isinstance(obj, (float, np.floating)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        else:
            return obj

    result = clean_json_values(result)
    return result




def start_comparison_sales(startLast, endLast, startThis, endThis):
    # --- Tải và clean ---
    df_this = download_and_clean(startThis, endThis, "this")
    df_last = download_and_clean(startLast, endLast, "last")

    # --- Gộp ---
    df_all = pd.concat([df_this, df_last], ignore_index=True)
    df_all = df_all.drop(columns=["startDate", "endDate"], errors="ignore")
    # Đảm bảo mọi giá trị NaN trong cột numeric đều = 0
    df_all = df_all.fillna(0)

    # Không ghi file Excel ra ổ đĩa nữa
    # df_all.to_excel(os.path.join(SALES_FOLDER, "all_data.xlsx"), index=False)
    # --- Summary ---
    summary = make_summary(df_all)

    return summary  # trả về dict thay vì in


def export_summary_to_excel(summary: dict):
    """
    Xuất summary (dict) ra file Excel nhiều sheet trong bộ nhớ (trả về bytes):
    - Sheet 'Summary'
    - Sheet 'Detail'
    """
    summary_df = pd.DataFrame({
        metric: summary["Summary"][metric]
        for metric in summary["Summary"]
    }).T.reset_index().rename(columns={"index": "Metric"})

    detail_records = []
    for shift, data in summary.items():
        if shift == "Summary":
            continue
        for metric, values in data.items():
            detail_records.append({
                "Shift": shift,
                "Metric": metric,
                **values
            })
    detail_df = pd.DataFrame(detail_records)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        detail_df.to_excel(writer, sheet_name="Detail", index=False)
    output.seek(0)
    return output.getvalue()
