import os
import pandas as pd
import io
from loginCirclek import get_session_token
from ExportFile import export_dep_report, download_exported_file, exp_check
from login_utils import get_login_info
# ===========================
# Cấu hình chung
# ===========================
BASE_PATH = r'C:\Users\SG0xxx-Tablet\Documents\SM\TOOL BCS\Order\order-backend'
DEPT_FOLDER = os.path.join(BASE_PATH, 'Data', 'Department')
os.makedirs(DEPT_FOLDER, exist_ok=True)

# Biến điều khiển: True = xử lý trên RAM, False = xử lý file vật lý
USE_MEMORY = False


# ===========================
# Download & Clean
# ===========================
def clean_excel(file_input, period, startDate, endDate):
    """
    Đọc file Excel từ bytes trong bộ nhớ hoặc từ file vật lý:
    - Bỏ 3 dòng đầu
    - Xóa cột thừa
    - Thêm metadata: period, startDate, endDate
    """
    if USE_MEMORY:
        df = pd.read_excel(io.BytesIO(file_input), header=None, engine="openpyxl")
    else:
        df = pd.read_excel(file_input, header=None, engine="openpyxl")
    df = df.iloc[2:].reset_index(drop=True)
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)

    cols_to_drop = ["Store Name", "Top Department", "Area Manager ID",
                    "Area Manager Name", "Store No.", "NO"]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    df["period"] = period
    df["startDate"] = startDate
    df["endDate"] = endDate
    return df


def download_and_clean(start, end, period_name):
    store_cd = get_login_info("store_cd")

    """
    Xuất dữ liệu từ API → tải về → clean (RAM hoặc file).
    """
    session_id = get_session_token()
    exp_key = export_dep_report(session_id, store_cd, start, end)
    if exp_check(session_id, exp_key):

        file_path = download_exported_file(exp_key, session_id,
                                       folder_path=DEPT_FOLDER,
                                       filename=f"{period_name}_{start}-{end}")
    if USE_MEMORY:
        with open(file_path, "rb") as f:
            file_content = f.read()
        try:
            os.remove(file_path)
        except Exception:
            pass
        return clean_excel(file_content, period_name, start, end)
    else:
        return clean_excel(file_path, period_name, start, end)


# ===========================
# Pivot & Format
# ===========================
def move_after(cols, col, after_col):
    """Đổi vị trí cột trong DataFrame (col đặt ngay sau after_col)."""
    if col in cols and after_col in cols:
        cols.remove(col)
        idx = cols.index(after_col)
        cols.insert(idx + 1, col)
    return cols


def pivot_and_format(df, index_cols, periods, num_days_this, num_days_last):
    """
    Pivot theo index_cols, tính:
    - this, last (doanh thu/ngày)
    - diff, percent
    - ratio so với tổng
    - Thêm dòng Total
    """
    pivot = df.pivot_table(
        index=index_cols,
        columns="period",
        values="Sales Amount",
        aggfunc="sum",
        fill_value=0
    )
    pivot = pivot.reindex(columns=periods)

    if all(p in pivot.columns for p in periods):
        pivot["this"] = pivot["this"] / num_days_this
        pivot["last"] = pivot["last"] / num_days_last
        pivot["diff"] = pivot["this"] - pivot["last"]
        pivot["percent"] = pivot.apply(
                lambda row: 1.0 if row["last"] == 0 and row["this"] > 0 else (row["diff"] / row["last"] if row["last"] != 0 else 0),
                axis=1
            )

        # Tính tỷ trọng
        total_this = pivot["this"].sum()
        total_last = pivot["last"].sum()
        total_diff = pivot["diff"].sum()
        total_percent = total_diff / total_last if total_last != 0 else pd.NA

        pivot["this_ratio"] = pivot["this"] / total_this if total_this != 0 else pd.NA
        pivot["last_ratio"] = pivot["last"] / total_last if total_last != 0 else pd.NA

        # Dòng tổng
        total_row = pd.DataFrame({
            "this": [total_this],
            "last": [total_last],
            "diff": [total_diff],
            "percent": [total_percent],
            "this_ratio": [1.0],
            "last_ratio": [1.0],
        }, index=pd.MultiIndex.from_tuples(
            [("Total",) * len(index_cols)], names=index_cols
        ))

        pivot = pd.concat([pivot, total_row])

        # Sắp xếp cột
        cols = pivot.columns.tolist()
        cols = move_after(cols, "this_ratio", "this")
        cols = move_after(cols, "last_ratio", "last")
        pivot = pivot[cols]

    pivot = pivot.reset_index()
    return pivot


# ===========================
# Tính toán top tăng/giảm
# ===========================
def get_top_diff(df, n=3):
    """
    Lấy top n tăng/giảm mạnh nhất theo diff.
    Loại bỏ dòng 'Total'.
    """
    df_filtered = df[~df['index'].astype(str).str.contains('Total')]
    top_increase = df_filtered.sort_values("diff", ascending=False).head(n)
    top_decrease = df_filtered.sort_values("diff", ascending=True).head(n)
    return {
        "increase": top_increase[["index", "diff"]].to_dict(orient="records"),
        "decrease": top_decrease[["index", "diff"]].to_dict(orient="records"),
    }


def attach_top_subcategory(dept_df, subcat_df, n_dept=3, n_sub=3):
    """
    Với mỗi department tăng mạnh nhất → lấy thêm top subcategory tăng mạnh nhất.
    """
    result = {"increase": [], "decrease": []}

    # Top department
    top_dept = get_top_diff(dept_df, n=n_dept)

    for key in ["increase", "decrease"]:
        for item in top_dept[key]:
            dept_name = item["index"]

            # Lọc subcategory của Dept này
            subcat_filtered = subcat_df[
                (subcat_df["Department"] == dept_name) &
                (~subcat_df["Sub-Category"].astype(str).str.contains("Total"))
            ]

            # Lấy top sub tăng/giảm
            if key == "increase":
                top_sub = subcat_filtered.sort_values("diff", ascending=False).head(n_sub)
            else:
                top_sub = subcat_filtered.sort_values("diff", ascending=True).head(n_sub)

            item["top_subCategory"] = top_sub[["Sub-Category", "diff"]].to_dict(orient="records")
            result[key].append(item)

    return result


# ===========================
# Main function
# ===========================
def start_comparison_department(startLast, endLast, startThis, endThis):
    periods = ["last", "this"]

    # --- Download & merge ---
    df_this = download_and_clean(startThis, endThis, "this")
    df_last = download_and_clean(startLast, endLast, "last")
    df_all = pd.concat([df_this, df_last], ignore_index=True)

    # Loại bỏ department Services
    df_all = df_all[df_all["Department"] != "19 Services"]

    # --- Số ngày ---
    num_days_this = (pd.to_datetime(endThis) - pd.to_datetime(startThis)).days + 1
    num_days_last = (pd.to_datetime(endLast) - pd.to_datetime(startLast)).days + 1

    # --- Pivot ---
    dept_df = pivot_and_format(df_all, ["Department"], periods, num_days_this, num_days_last)
    cat_df = pivot_and_format(df_all, ["Department", "Category"], periods, num_days_this, num_days_last)
    subcat_df = pivot_and_format(df_all, ["Department", "Category", "Sub-Category"], periods, num_days_this, num_days_last)

    # --- Xuất JSON ---
    json_output = {
        "department": dept_df.fillna(0).to_dict(orient="records"),
        "category": cat_df.fillna(0).to_dict(orient="records"),
        "subCategory": subcat_df.fillna(0).to_dict(orient="records"),
        "topDiff": attach_top_subcategory(dept_df, subcat_df, n_dept=3, n_sub=3)
    }

    return json_output
