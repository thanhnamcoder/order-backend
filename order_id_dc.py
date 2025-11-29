import requests
import json
import datetime
import pandas as pd
from loginCirclek import get_session_token
from RealTimmInventory import get_inventory

def get_order_info(session_id, store_cd, start_date, end_date):
    """
    Lấy danh sách orderId, orderDate, deliveryDate từ API Circle K
    """
    search_json = {
        "regionCd": "",
        "cityCd": "",
        "districtCd": "",
        "storeCd": store_cd,
        "orderId": "",
        "reviewStatus": "",
        "orderMethod": "",
        "orderDifferentiate": "1",
        "orderDirectSupplierDateStartDate": start_date,
        "orderDirectSupplierDateEndDate": end_date,
        "optionTime": "orderDate",
        "allocation": "",
        "isAllocation": "0"
    }

    search_json_str = json.dumps(search_json, separators=(",", ":"))
    url = (
        "https://ss.circlek.com.vn/scmaster/a/cdOrder/getOrderCdInfor"
        f"?page=1&rows=10000&sidx=id&sord=desc&searchJson={search_json_str}"
    )

    headers = {
        "user-agent": "Mozilla/5.0",
        "cookie": f"SESSION={session_id}",
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"⚠️ Lỗi lấy danh sách order: {response.status_code}")
        return []

    try:
        data = response.json()
    except json.JSONDecodeError:
        print("⚠️ Không phải JSON, có thể session hết hạn.")
        return []

    # Đảm bảo data là dict và rows là list
    if not isinstance(data, dict):
        print("⚠️ Dữ liệu trả về không phải dict.")
        return []
    rows = data.get("rows")
    if not isinstance(rows, list):
        rows = []
    result = []
    for r in rows:
        result.append({
            "orderId": r.get("orderId"),
            "orderDate": r.get("orderDate"),
            "deliveryDate": r.get("deliveryDate"),
            "storeCd": r.get("storeCd"),
            "storeName": r.get("storeName"),
            "vendorId": r.get("vendorId"),
        })
    return result


def get_items_by_order(session_id, orderId, orderDate, storeCd, storeName, vendorId):
    """
    Lấy chi tiết sản phẩm của 1 orderId cụ thể
    """
    search_json = {
        "orderId": orderId,
        "orderDate": orderDate,
        "storeCd": storeCd,
        "storeName": storeName,
        "vendorId": vendorId
    }

    search_json_str = json.dumps(search_json, ensure_ascii=False, separators=(",", ":"))
    url = (
        "https://ss.circlek.com.vn/scmaster/a/cdOrder/getItemsByOrder"
        f"?page=1&rows=10000&sidx=id&sord=desc&searchJson={requests.utils.quote(search_json_str)}"
    )

    headers = {
        "user-agent": "Mozilla/5.0",
        "cookie": f"SESSION={session_id}",
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"⚠️ Lỗi lấy item cho {orderId}: {response.status_code}")
        return []

    try:
        data = response.json()
    except json.JSONDecodeError:
        print(f"⚠️ Lỗi parse JSON cho order {orderId}")
        return []

    return data.get("rows", [])


def daterange(start_date, end_date):
    """
    Tạo danh sách ngày giữa start_date và end_date
    """
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + datetime.timedelta(n)


# ---------------------------
# 🔹 CHƯƠNG TRÌNH CHÍNH
# ---------------------------
if __name__ == "__main__":
    session_id = get_session_token()
    store_cd = "SG0330"

    # khoảng thời gian cần quét
    start_date = datetime.date(2025, 10, 10)
    end_date = datetime.date(2025, 10, 12)
    print(end_date)
    today = datetime.date.today()
    today_str = today.strftime("%Y%m%d")
    # ✅ Lấy dữ liệu realtime inventory
    realtime = get_inventory(session_id, store_cd, today_str)
    # print("📦 Dữ liệu realtime:")
    # print(realtime)

    all_data = []

    # ✅ Quét order theo từng ngày
    for single_date in daterange(start_date, end_date):
        date_str = single_date.strftime("%Y%m%d")
        print(f"\n📅 Đang xử lý ngày {date_str}...")

        orders = get_order_info(session_id, store_cd, date_str, date_str)
        if not orders:
            print("   ⛔ Không có order nào trong ngày này.")
            continue

        for o in orders:
            items = get_items_by_order(
                session_id=session_id,
                orderId=o["orderId"],
                orderDate=o["orderDate"],
                storeCd=o["storeCd"],
                storeName=o["storeName"],
                vendorId=o["vendorId"],
            )
            for it in items:
                all_data.append({
                    "date": date_str,
                    "orderId": o["orderId"],
                    "orderDate": o["orderDate"],
                    "deliveryDate": o["deliveryDate"],
                    "storeCd": o["storeCd"],
                    "articleId": it.get("articleId"),
                    "articleName": it.get("articleName"),
                    "orderQty": it.get("orderQty"),
                    "receiveQty": it.get("receiveQty"),
                    "vendorId": o["vendorId"],
                })

    # ✅ Sau khi quét hết ngày → gộp vào 1 file Excel
    if all_data:
        df = pd.DataFrame(all_data)
        df.sort_values(by=["date", "storeCd", "orderId"], inplace=True)

        # ✅ Thêm realtimeQty nếu có dữ liệu realtime
        realtime_data = realtime.get("rows", [])
        if realtime_data:
            realtime_df = pd.DataFrame(realtime_data)[["itemCode", "realtimeQty"]]
            realtime_df.rename(columns={"itemCode": "articleId"}, inplace=True)
            df = pd.merge(df, realtime_df, on="articleId", how="left")
            df["realtimeQty"].fillna(0, inplace=True)
        else:
            df["realtimeQty"] = 0

        # ✅ Xuất Excel
        output_file = f"Data\DC\orders_{start_date}_{end_date}.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\n✅ Đã lưu toàn bộ {len(df)} dòng vào file: {output_file}")
    else:
        print("\n⚠️ Không có dữ liệu nào trong toàn bộ khoảng thời gian.")
