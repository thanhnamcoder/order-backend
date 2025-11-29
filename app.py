
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
import os
import json
import re
from GetItemWriteOff import get_quantity_item_write_off
from Compare_Department import start_comparison_department
from Compare_Sales import start_comparison_sales
from services.inventory_service import InventoryService
from utils.filter_utils import parse_list_param
from datetime import datetime
from services.promotion_service import parse_promotion_file
from werkzeug.utils import secure_filename

from services.wishlist_service import (
    remove_wishlist_code,
    save_json_to_file,
    get_wishlist_data,
    save_wishlist_data
)
from services.writeoff_service import normalize_writeoff_payload
from login_utils import get_login_info
from loginCirclek import get_out_store_list
from POGCRAW import run_get_data_pog
from ExportFile import item_sell_by_store

app = Flask(__name__)
CORS(app, supports_credentials=True)
@app.route("/upload-promotion", methods=["POST", "OPTIONS"])
def upload_promotion():
    """
    Receive uploaded promotion file (multipart/form-data, field name 'file')
    and save it under promotion/data/ with a timestamped filename.
    Supports OPTIONS preflight for CORS.
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        headers = response.headers
        headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        headers["Access-Control-Allow-Headers"] = request.headers.get("Access-Control-Request-Headers", "Content-Type")
        headers["Access-Control-Allow-Credentials"] = "true"
        return response, 200

    try:
        if 'file' not in request.files:
            # Return diagnostic info to help debug why file part is missing
            info = {
                "error": "No file part in the request",
                "content_type": request.headers.get("Content-Type"),
                "files_keys": list(request.files.keys()),
                "form_keys": list(request.form.keys()),
                "content_length": request.headers.get("Content-Length"),
            }
            return jsonify(info), 400

        f = request.files['file']
        if not f or f.filename == '':
            return jsonify({"error": "No selected file"}), 400

        filename = secure_filename(f.filename)
        save_dir = os.path.join('promotion', 'data')
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        dest_name = f"{ts}_{filename}"
        dest_path = os.path.join(save_dir, dest_name)

        f.save(dest_path)

        # Try to parse the saved file into structured JSON using the promotion service
        try:
            parsed_rows = parse_promotion_file(dest_path, filename)

            # persist parsed JSON into Data/Promotion as a fixed filename 'promotion.json'
            json_dir = os.path.join('Data', 'Promotion')
            os.makedirs(json_dir, exist_ok=True)
            fixed_json_name = 'promotion.json'
            fixed_json_path = os.path.join(json_dir, fixed_json_name)
            try:
                with open(fixed_json_path, 'w', encoding='utf-8') as fj:
                    json.dump(parsed_rows, fj, ensure_ascii=False, indent=2)
            except Exception as jex:
                # non-fatal: still return parsed data but include save error
                return jsonify({
                    "message": "saved_and_parsed",
                    "filename": dest_name,
                    "path": dest_path,
                    "data": parsed_rows,
                    "json_save_error": str(jex)
                }), 200

            return jsonify({"message": "saved_and_parsed", "filename": dest_name, "path": dest_path, "data": parsed_rows, "fixed_json_name": fixed_json_name, "fixed_json_path": fixed_json_path}), 200
        except Exception as exc:
            return jsonify({"message": "saved", "filename": dest_name, "path": dest_path, "parse_error": str(exc)}), 200
    except Exception as exc:
        return jsonify({"error": "Failed to save file", "details": str(exc)}), 500
@app.route("/store-code", methods=["GET"])
def get_store_code():
    """
    Return the current store code and store name retrieved from login info.
    """
    try:
        store_code = get_login_info("store_cd")
        store_name = get_login_info("store_name")

        if not store_code:
            return jsonify({"error": "Store code not found"}), 404

        return jsonify({
            "store_code": store_code,
            "store_name": store_name
        }), 200
    except Exception as exc:
        return jsonify({
            "error": "Failed to get store_code",
            "details": str(exc)
        }), 500
# --- Wishlist API ---
@app.route("/remove-wishlist", methods=["POST"])
def remove_wishlist():
    """
    Nhận dữ liệu JSON với 'code', xóa khỏi file Data/WishlistData.json nếu tồn tại.
    """
    try:
        data = request.get_json(force=True)
    except Exception as exc:
        return jsonify({"error": "Invalid JSON", "details": str(exc)}), 400

    code_to_remove = None
    category = None
    if isinstance(data, dict) and "code" in data:
        code_to_remove = data["code"]
        category = data.get("category")
    if not code_to_remove:
        return jsonify({"error": "Missing 'code' in request"}), 400

    try:
        result = remove_wishlist_code(code_to_remove, category=category)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": "Failed to remove code", "details": str(exc)}), 500


@app.route("/wishlist", methods=["GET"])
def get_wishlist():
    """
    Đọc file Data/WishlistData.json và trả về dữ liệu wishlist (mảng) only.
    """
    try:
        wishlist_data = get_wishlist_data()
        return jsonify({
            "wishlist": wishlist_data
        }), 200
    except Exception as exc:
        return jsonify({
            "error": "Failed to read data",
            "details": str(exc)
        }), 500


@app.route("/write-off", methods=["GET", "POST"])
def write_off_route():
    """
    GET: Return write_off_data only (from GetItemWriteOff.get_quantity_item_write_off).
    POST: Receive JSON payload from frontend (expected shape: { itemCodes: [], quantities: [] })
          Validate, normalize into items and save to Data/WriteOff/writeoff_result_<timestamp>.json
    """
    if request.method == "GET":
        try:
            write_off_data = get_quantity_item_write_off()
            return jsonify({
                "write_off_data": write_off_data
            }), 200
        except Exception as exc:
            return jsonify({
                "error": "Failed to read write off data",
                "details": str(exc)
            }), 500

    # POST handling: normalize payload using service and return items (no file save)
    try:
        data = request.get_json(force=True)
    except Exception as exc:
        return jsonify({"error": "Invalid JSON", "details": str(exc)}), 400

    try:
        items = normalize_writeoff_payload(data)
    except ValueError as ve:
        return jsonify({"error": "Invalid payload", "details": str(ve)}), 400
    except Exception as exc:
        return jsonify({"error": "Failed to process payload", "details": str(exc)}), 500

    # Fetch cost info for the provided item codes using the GetAmountCost helper
    try:
        item_codes = [it.get("item_code") for it in items if it.get("item_code")]
        from services.writeoff_service import fetch_costs_for_items

        # Attempt to use a local cache first to avoid unnecessary remote calls.
        cache_dir = os.path.join("Data", "WriteOff")
        cache_file = os.path.join(cache_dir, "costs_cache.json")

        costs_map = {}
        cache_map = {}
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as cf:
                    cache_map = json.load(cf) or {}
                    # ensure keys are strings
                    cache_map = {str(k): v for k, v in cache_map.items()}
        except Exception:
            # non-fatal: treat as empty cache
            cache_map = {}

        # fill costs_map from cache where possible
        missing_codes = []
        for code in item_codes:
            key = str(code)
            if key in cache_map:
                costs_map[key] = cache_map[key]
            else:
                missing_codes.append(code)

        # Fetch only the missing codes from upstream
        fetched_list = []
        if missing_codes:
            fetched_list = fetch_costs_for_items(missing_codes) or []
            # normalize fetched list and merge into maps
            for c in fetched_list:
                try:
                    k = str(c.get("itemCode") or c.get("item_code") or c.get("itemCode"))
                except Exception:
                    k = None
                if k:
                    costs_map[k] = c
                    cache_map[k] = c

        # persist updated cache (best-effort)
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as cf:
                json.dump(cache_map, cf, indent=2, ensure_ascii=False)
        except Exception:
            # ignore cache write failures
            pass

        # Merge cost info into items and compute amount_write_off
        total_amount = 0.0
        for it in items:
            code = it.get("item_code")
            cost_info = costs_map.get(str(code)) if code is not None else None
            it["cost_info"] = cost_info

            # compute amount_write_off = baseOrderPrice * quantity
            amount = None
            try:
                qty = it.get("quantity")
                # qty may be string/float/int/None
                qv = None
                if qty is None:
                    qv = None
                elif isinstance(qty, (int, float)):
                    qv = float(qty)
                else:
                    qv = float(str(qty).replace(",", ""))

                base = None
                if cost_info and ("baseOrderPrice" in cost_info):
                    base = cost_info.get("baseOrderPrice")
                    # try to coerce to float
                    if isinstance(base, (int, float)):
                        bv = float(base)
                    else:
                        bv = float(str(base).replace(",", ""))
                else:
                    bv = None

                if qv is not None and bv is not None:
                    amount = bv * qv
                    # round to 2 decimals if not integer
                    if abs(amount - int(amount)) > 1e-9:
                        amount = round(amount, 2)
                    else:
                        amount = int(amount)
                    total_amount += float(amount)
                else:
                    amount = None
            except Exception:
                amount = None

            it["amount_write_off"] = amount
    except Exception as exc:
        # Non-fatal: still return normalized items but include an error note
        return jsonify({"items": items, "count": len(items), "costs_error": str(exc)}), 200

    # include total amount (rounded to 2 decimals when needed)
    total_amount_val = None
    try:
        if total_amount is not None:
            # if integer-like, return int, else round to 2 decimals
            if abs(total_amount - int(total_amount)) > 1e-9:
                total_amount_val = round(total_amount, 2)
            else:
                total_amount_val = int(total_amount)
    except Exception:
        total_amount_val = None

    # Build compact mapping keyed by item_code with requested fields
    compact = {}
    for it in items:
        code = it.get("item_code")
        if not code:
            continue
        cost_info = it.get("cost_info") or {}
        compact[str(code)] = {
            "amount_write_off": it.get("amount_write_off"),
            # include original requested quantity so frontend can display it
            "quantity": it.get("quantity"),
            "barcode": cost_info.get("barcode"),
            "baseOrderPrice": cost_info.get("baseOrderPrice"),
            "itemName": cost_info.get("itemName"),
        }

    return jsonify({"items": compact, "count": len(compact), "total_amount_write_off": total_amount_val}), 200



@app.route("/save-json", methods=["POST"])
def save_json():
    """
    Nhận dữ liệu JSON từ client và lưu vào file Data/WishlistData.json.
    Nếu file chưa tồn tại thì tạo mới, nếu đã có thì ghi đè.
    """
    try:
        data = request.get_json(force=True)
    except Exception as exc:
        return jsonify({"error": "Invalid JSON", "details": str(exc)}), 400

    try:
        # accept either { code, category } or an array of such objects
        result = save_wishlist_data(data)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": "Failed to save file", "details": str(exc)}), 500
@app.route("/compare-periods", methods=["GET"])
def compare_periods_route():
    """
    Accepts query params: start1, end1, start2, end2.
    Optional: session_id, exclude_pma, normalize.
    Trả về dữ liệu department + sales trong cùng 1 response.
    """
    # required params (hỗ trợ alias)
    start1 = request.args.get('start1') or request.args.get('start_1') or request.args.get('startDate1')
    end1 = request.args.get('end1') or request.args.get('end_1') or request.args.get('endDate1')
    start2 = request.args.get('start2') or request.args.get('start_2') or request.args.get('startDate2')
    end2 = request.args.get('end2') or request.args.get('end_2') or request.args.get('endDate2')

    if not (start1 and end1 and start2 and end2):
        return jsonify({"error": "Missing required query params: start1, end1, start2, end2"}), 400

    try:
        department_data = start_comparison_department(start1, end1, start2, end2)
        sales_data = start_comparison_sales(start1, end1, start2, end2)

        return jsonify({
            "department": department_data,
            "sales": sales_data
        }), 200

    except Exception as exc:
        error_text = str(exc)


        # ❌ Lỗi khác
        return jsonify({"error": error_text}), 500


@app.route("/inventory", methods=["GET"])
def inventory():
    service = InventoryService()
    # Load current promotion codes (set of strings)
    def load_promotion_codes():
        try:
            ppath = os.path.join('Data', 'Promotion', 'promotion.json')
            if not os.path.exists(ppath):
                return set()
            with open(ppath, 'r', encoding='utf-8') as pf:
                pdata = json.load(pf)
            # pdata may be a dict like {"data": [...] } or a list
            arr = None
            if isinstance(pdata, dict) and 'data' in pdata:
                arr = pdata.get('data') or []
            elif isinstance(pdata, list):
                arr = pdata
            else:
                arr = []

            codes = set()
            for r in arr:
                if not isinstance(r, dict):
                    continue
                code = r.get('item_code') or r.get('itemCode') or r.get('code')
                if code is not None:
                    codes.add(str(code))
            return codes
        except Exception:
            return set()
    try:
        upstream_json = service.fetch_from_api()
    except Exception as exc:
        return jsonify({"error": "Failed to fetch API", "details": str(exc)}), 502

    rows = service.normalize_rows(upstream_json)

    # annotate rows with promotion flag
    promo_codes = load_promotion_codes()
    # annotate rows with pog flag (based on Data/POG_DATA/EXCEL/item_code.json)
    def load_pog_codes():
        try:
            ppath = os.path.join('Data', 'POG_DATA', 'JSON', 'item_code.json')
            if not os.path.exists(ppath):
                return set()
            with open(ppath, 'r', encoding='utf-8') as pf:
                pdata = json.load(pf)
            arr = None
            if isinstance(pdata, dict) and 'item_code' in pdata:
                arr = pdata.get('item_code') or []
            elif isinstance(pdata, list):
                arr = pdata
            else:
                arr = []
            codes = set()
            for v in arr:
                try:
                    if v is not None:
                        codes.add(str(v))
                except Exception:
                    continue
            return codes
        except Exception:
            return set()

    pog_codes = load_pog_codes()
    for r in rows:
        try:
            code = r.get('item_code') or r.get('itemCode') or r.get('code')
            r['promotion'] = (str(code) in promo_codes) if code is not None else False
            r['pog'] = (str(code) in pog_codes) if code is not None else False
        except Exception:
            r['promotion'] = False
            r['pog'] = False

    # filter
    item_codes = parse_list_param(request.args.get("itemCode") or request.args.get("itemcode"))
    item_barcodes = parse_list_param(request.args.get("itemBarcode") or request.args.get("itembarcode"))

    if not item_codes and not item_barcodes:
        # Return normalized rows (annotated with promotion flag)
        return jsonify(rows), 200

    matched = service.filter_rows(rows, item_codes, item_barcodes)

    # pagination
    page = int(request.args.get("page", 1))
    row_per_page = int(request.args.get("rowPerPage", request.args.get("rows", 10)))
    response = service.paginate(matched, page, row_per_page)
    # Ensure paginated items also include promotion flag (should already be annotated)
    # response is expected to contain items in a list under some structure; if it's a simple list, annotate just in case
    try:
        if isinstance(response, dict) and 'items' in response and isinstance(response['items'], list):
            for it in response['items']:
                # ensure both promotion and pog flags exist on paginated items
                code = it.get('item_code') or it.get('itemCode') or it.get('code')
                if 'promotion' not in it:
                    it['promotion'] = (str(code) in promo_codes) if code is not None else False
                if 'pog' not in it:
                    it['pog'] = (str(code) in pog_codes) if code is not None else False
        elif isinstance(response, list):
            for it in response:
                for it in response:
                    if isinstance(it, dict):
                        code = it.get('item_code') or it.get('itemCode') or it.get('code')
                        if 'promotion' not in it:
                            it['promotion'] = (str(code) in promo_codes) if code is not None else False
                        if 'pog' not in it:
                            it['pog'] = (str(code) in pog_codes) if code is not None else False
    except Exception:
        pass

    return jsonify(response), 200


@app.route("/inventory-file", methods=["GET"])
def inventory_file():
    service = InventoryService()
    # Prefer a specific saved response file (absolute path) when present.
    preferred_path = r"saved_responses\upstream_20250929_134458_570687.json"
    upstream_json = None
    if os.path.exists(preferred_path):
        try:
            with open(preferred_path, 'r', encoding='utf-8') as f:
                upstream_json = json.load(f)
        except Exception as exc:
            return jsonify({"error": "Failed to read preferred saved response file", "details": str(exc)}), 500
    else:
        try:
            upstream_json = service.fetch_from_file()
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    rows = service.normalize_rows(upstream_json)

    # annotate rows with promotion flag using the same helper
    def load_promotion_codes_local():
        try:
            ppath = os.path.join('Data', 'Promotion', 'promotion.json')
            if not os.path.exists(ppath):
                return set()
            with open(ppath, 'r', encoding='utf-8') as pf:
                pdata = json.load(pf)
            arr = None
            if isinstance(pdata, dict) and 'data' in pdata:
                arr = pdata.get('data') or []
            elif isinstance(pdata, list):
                arr = pdata
            else:
                arr = []
            codes = set()
            for r in arr:
                if not isinstance(r, dict):
                    continue
                code = r.get('item_code') or r.get('itemCode') or r.get('code')
                if code is not None:
                    codes.add(str(code))
            return codes
        except Exception:
            return set()

    promo_codes = load_promotion_codes_local()
    # load POG item codes for local file-based inventory
    def load_pog_codes_local():
        try:
            ppath = os.path.join('Data', 'POG_DATA', 'JSON', 'item_code.json')
            if not os.path.exists(ppath):
                return set()
            with open(ppath, 'r', encoding='utf-8') as pf:
                pdata = json.load(pf)
            arr = None
            if isinstance(pdata, dict) and 'item_code' in pdata:
                arr = pdata.get('item_code') or []
            elif isinstance(pdata, list):
                arr = pdata
            else:
                arr = []
            codes = set()
            for v in arr:
                try:
                    if v is not None:
                        codes.add(str(v))
                except Exception:
                    continue
            return codes
        except Exception:
            return set()

    pog_codes = load_pog_codes_local()
    for r in rows:
        try:
            code = r.get('item_code') or r.get('itemCode') or r.get('code')
            r['promotion'] = (str(code) in promo_codes) if code is not None else False
            r['pog'] = (str(code) in pog_codes) if code is not None else False
        except Exception:
            r['promotion'] = False
            r['pog'] = False

    # filter
    item_codes = parse_list_param(request.args.get("itemCode") or request.args.get("itemcode"))
    item_barcodes = parse_list_param(request.args.get("itemBarcode") or request.args.get("itembarcode"))

    if not item_codes and not item_barcodes:
        return jsonify(rows), 200

    matched = service.filter_rows(rows, item_codes, item_barcodes)

    # pagination
    page = int(request.args.get("page", 1))
    row_per_page = int(request.args.get("rowPerPage", request.args.get("rows", 10)))
    response = service.paginate(matched, page, row_per_page)

    return jsonify(response), 200


@app.route("/pog/fetch", methods=["GET", "POST", "OPTIONS"])
def pog_fetch_router():
    """Trigger extraction of planogram Excel files (run_get_data_pog).

    By default this starts the job in a background thread and returns 202.
    If the client requests blocking mode (send JSON {"wait": true} or ?wait=1)
    the route will run synchronously and return 200 when finished.
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        headers = response.headers
        headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        headers["Access-Control-Allow-Headers"] = request.headers.get("Access-Control-Request-Headers", "Content-Type")
        headers["Access-Control-Allow-Credentials"] = "true"
        return response, 200

    # Default: wait for the job to finish (blocking). For backward compatibility
    # the client can request background execution using JSON {"background": true}
    # or query param ?background=1; if 'wait' is explicitly provided use it.
    # Support optional 'wait' flag (blocking) via JSON or query param
    body = {}
    try:
        body = request.get_json(force=False) or {}
    except Exception:
        body = {}

    # default: wait/block
    wait_flag = True

    # if the client supplies explicit "wait" use that
    if isinstance(body, dict) and body.get("wait") is not None:
        wait_flag = str(body.get("wait")).lower() in ("1", "true", "yes", "y")
    elif request.args.get("wait") is not None:
        wait_flag = str(request.args.get("wait")).lower() in ("1", "true", "yes", "y")

    # allow explicit "background" flag to run in background instead
    if isinstance(body, dict) and body.get("background") is not None:
        bg = str(body.get("background")).lower() in ("1", "true", "yes", "y")
        if bg:
            wait_flag = False
    elif request.args.get("background") is not None:
        bg = str(request.args.get("background")).lower() in ("1", "true", "yes", "y")
        if bg:
            wait_flag = False

    # Accept file_type and other params from body or query string
    file_type = None
    if isinstance(body, dict) and body.get("file_type") is not None:
        file_type = str(body.get("file_type")).lower()
    elif request.args.get("file_type") is not None:
        file_type = str(request.args.get("file_type")).lower()
    # Default to 'excel' if not provided
    if not file_type:
        file_type = "excel"

    try:
        if wait_flag:
            # run synchronously, trả về kết quả chi tiết
            result = run_get_data_pog(file_type=file_type)
            return jsonify(result), 200
        else:
            # start in background and return immediately
            import threading
            def run_and_log():
                try:
                    run_get_data_pog(file_type=file_type)
                except Exception as exc:
                    # Có thể ghi log nếu cần
                    pass
            t = threading.Thread(target=run_and_log, daemon=True)
            t.start()
            return jsonify({"message": "POG fetch started (background)", "file_type": file_type}), 202

    except Exception as exc:
        return jsonify({"error": "Failed to start POG fetch", "details": str(exc)}), 500
import os
import json
from flask import request, jsonify

@app.route("/submit-store-data", methods=["POST"])
def submit_store_data():
    """
    Nhận dữ liệu từ frontend: storeCode, start1, end1, start2, end2
    Sau đó cập nhật store_cd trong Data/Login/user_login.json nếu có.
    """
    try:
        data = request.get_json(force=True)
        store_code = (data.get("storeCode") or "").strip()

        # 📌 Nếu storeCode rỗng thì không cập nhật — nhưng vẫn trả OK
        if not store_code:
            return jsonify({
                "message": "No store code provided — skipped update",
                "updated": False
            }), 200

        # 🗂️ Đường dẫn tới file user_login.json
        file_path = os.path.join("Data", "Login", "user_login.json")

        # Kiểm tra file tồn tại
        if not os.path.exists(file_path):
            return jsonify({"error": f"File not found: {file_path}"}), 404

        # Đọc nội dung hiện tại
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                user_data = json.load(f)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON format in user_login.json"}), 500

        # ✅ Cập nhật store_cd
        old_store_cd = user_data.get("store_cd")
        user_data["store_cd"] = store_code

        # Cố gắng lấy store_name từ API get_out_store_list và lưu vào file
        try:
            store_info = get_out_store_list(store_cd=store_code)
            # get_out_store_list trả về dict {k,v} hoặc None
            store_name = None
            if isinstance(store_info, dict):
                store_name = store_info.get("v")
            # Lưu cả store_name (nếu có) vào user_data
            user_data["store_name"] = store_name
        except Exception as exc:
            # Không block việc lưu store_cd nếu không lấy được tên cửa hàng
            user_data["store_name"] = None

        # Ghi lại file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            "message": "Store code updated successfully!",
            "updated": True,
            "old_store_cd": old_store_cd,
            "new_store_cd": store_code,
            "user_data": user_data
        }), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/promotion", methods=["GET"])
def get_promotion_json():
    """Return the fixed promotion JSON saved at Data/Promotion/promotion.json"""
    try:
        json_path = os.path.join('Data', 'Promotion', 'promotion.json')
        if not os.path.exists(json_path):
            return jsonify({"error": "No promotion JSON found"}), 404
        with open(json_path, 'r', encoding='utf-8') as jf:
            data = json.load(jf)
        return jsonify({"data": data}), 200
    except Exception as exc:
        return jsonify({"error": "Failed to read promotion JSON", "details": str(exc)}), 500



@app.route("/item_sell_by_store", methods=["POST", "OPTIONS"])
def item_sell_by_store_router():
    # Xử lý preflight CORS (OPTIONS)
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        headers = response.headers
        headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        headers["Access-Control-Allow-Headers"] = request.headers.get(
            "Access-Control-Request-Headers", "Content-Type"
        )
        headers["Access-Control-Allow-Credentials"] = "true"
        return response, 200

    try:
        data = request.get_json(force=True)
    except Exception as exc:
        return jsonify({"error": "Invalid JSON", "details": str(exc)}), 400

    type_ = data.get("type")
    name_raw = data.get("name")
    this_range = data.get("thisRange") or []
    last_range = data.get("lastRange") or []

    # --------------------------
    # 🔧 Hàm chuẩn hóa ngày sang yyyymmdd
    # --------------------------
    def first_day_of_month(date_str):
        """Nhận yyyymmdd → trả về yyyymm01"""
        if not date_str or len(date_str) != 8:
            return date_str
        return date_str[:6] + "01"

    def normalize_date(date_value):
        if not date_value:
            return None
        if isinstance(date_value, (int, float)):
            return f"{int(date_value):08d}"
        if isinstance(date_value, str):
            date_value = date_value.strip()
            # Nếu đã đúng dạng yyyymmdd
            if re.match(r"^\d{8}$", date_value):
                return date_value
            # Nếu là dạng yyyy-mm-dd hoặc yyyy/mm/dd
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    d = datetime.strptime(date_value, fmt)
                    return d.strftime("%Y%m%d")
                except ValueError:
                    continue
        return None

    # --------------------------
    # 🧭 Chuẩn hóa this_range & last_range
    # --------------------------
    this_start = normalize_date(this_range[0]) if len(this_range) > 0 else None
    this_end = normalize_date(this_range[1]) if len(this_range) > 1 else None
    last_start = normalize_date(last_range[0]) if len(last_range) > 0 else None
    last_end = normalize_date(last_range[1]) if len(last_range) > 1 else None

    # 🔥 ép ngày đầu tháng
    if this_start:
        this_start = first_day_of_month(this_start)
    if last_start:
        last_start = first_day_of_month(last_start)

    print(f"this_start={this_start}, this_end={this_end}")
    print(f"last_start={last_start}, last_end={last_end}")


    # --------------------------
    # Xử lý code + name
    # --------------------------
    name_code = None
    name = None
    if isinstance(name_raw, str):
        m = re.match(r"^\s*([0-9]+)\s*(.*)$", name_raw)
        if m:
            name_code = m.group(1)
            rest = m.group(2).strip()
            name = rest if rest else None

    explicit_code = data.get("code")
    code_value = str(explicit_code) if explicit_code not in (None, "") else name_code

    # --------------------------
    # Xác định cấp độ
    # --------------------------
    department_cd = category_cd = subCategory_cd = None
    t = (type_ or "").strip().lower()
    if t in ("department", "dep", "d", "dept"):
        department_cd = code_value
    elif t in ("category", "cat", "c"):
        category_cd = code_value
    elif t in ("subcategory", "sub_category", "sub-category", "sub", "s", "subcat"):
        subCategory_cd = code_value

    try:
        items_this = []
        items_last = []

        if this_start:
            items_this = item_sell_by_store(this_start, this_end, department_cd, category_cd, subCategory_cd)
        if last_start:
            items_last = item_sell_by_store(last_start, last_end, department_cd, category_cd, subCategory_cd)

        return jsonify({
            "this": {
                "start_date": this_start,
                "end_date": this_end,
                "items": items_this
            },
            "last": {
                "start_date": last_start,
                "end_date": last_end,
                "items": items_last
            }
        }), 200

    except Exception as exc:
        return jsonify({"error": "Failed to fetch items", "details": str(exc)}), 500

from flask import send_from_directory

# Serve static POG Excel files for download
@app.route('/static/POG_DATA/EXCEL/<path:filename>', methods=['GET'])
def serve_pog_excel_file(filename):
    base_dir = os.path.join('Data', 'POG_DATA', 'EXCEL')
    # Security: only allow files under this directory
    return send_from_directory(base_dir, filename, as_attachment=True)

if __name__ == '__main__':
    # Serve static POG PDF files for download
    @app.route('/static/POG_DATA/PDF/<path:filename>', methods=['GET'])
    def serve_pog_pdf_file(filename):
        base_dir = os.path.join('Data', 'POG_DATA', 'PDF')
        # Security: only allow files under this directory
        return send_from_directory(base_dir, filename, as_attachment=True)
    app.run(host='0.0.0.0', port=5000, debug=True)

