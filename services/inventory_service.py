import requests, os, json
from datetime import datetime
from urllib.parse import urlencode
from login_utils import get_login_info

class InventoryService:
    BASE_URL = "https://ss.circlek.com.vn/scmaster/a/rtInventoryQuery/getInventory"
    def __init__(self):
        self.store_cd = get_login_info("store_cd")
        print(self.store_cd)
    # ----------- Data Source -----------
    def fetch_from_api(self):
        """Lấy dữ liệu inventory từ CircleK API"""
        search = self._build_search_payload()
        params = self._build_query_params(search)
        url = f"{self.BASE_URL}?{urlencode(params)}"
        resp = requests.get(url, timeout=10)
        return resp.json()

    def fetch_from_file(self):
        """Đọc file JSON mới nhất trong saved_responses"""
        files = sorted(
            [os.path.join("saved_responses", f) for f in os.listdir("saved_responses") if f.endswith(".json")],
            key=os.path.getmtime,
            reverse=True,
        )
        if not files:
            raise FileNotFoundError("No saved json file found")
        with open(files[0], "r", encoding="utf-8") as f:
            return json.load(f)

    # ----------- Business Logic -----------
    def normalize_rows(self, upstream_json):
        """Chuẩn hóa rows từ API hoặc file"""
        rows = []
        if isinstance(upstream_json, dict):
            if isinstance(upstream_json.get("rows"), list):
                rows = upstream_json["rows"]
            elif isinstance(upstream_json.get("results"), list):
                for r in upstream_json["results"]:
                    if isinstance(r, dict) and isinstance(r.get("rows"), list):
                        rows.extend(r["rows"])
        elif isinstance(upstream_json, list):
            rows = upstream_json
        return rows

    def filter_rows(self, rows, item_codes, item_barcodes):
        """Lọc rows theo itemCode hoặc itemBarcode"""
        def matches(row):
            code = str(row.get("itemCode") or row.get("item_code") or "")
            barcode = str(row.get("itemBarcode") or row.get("item_barcode") or row.get("barcode") or "")
            return (code in item_codes) or (barcode in item_barcodes)
        return [r for r in rows if matches(r)]

    def paginate(self, rows, page, row_per_page):
        """Tính phân trang"""
        records = len(rows)
        total = (records + row_per_page - 1) // row_per_page if row_per_page > 0 else 0
        return {
            "rows": rows,
            "page": page,
            "records": records,
            "rowPerPage": row_per_page,
            "total": total,
            "message": None,
        }

    # ----------- Internal Utils -----------
    def _build_search_payload(self):
        today = datetime.now().strftime("%Y%m%d")
        return {
            "storeCd": self.store_cd,
            "stockDate": today,
            "itemCode": "",
            "itemBarcode": "",
            "depId": "",
            "pmaId": "",
            "categoryId": "",
            "omCode": "",
            "ofcCode": "",
            "subCategoryId": "",
            "vendorId": "",
        }

    def _build_query_params(self, search):
        return {
            "page": 1,
            "rows": 1000000,
            "sidx": "id",
            "sord": "desc",
            "searchJson": json.dumps(search),
            "_": 1756101240451,
        }
