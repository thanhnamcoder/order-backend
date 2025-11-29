import os
from typing import List, Dict, Any

import pandas as pd
from pyexcel_ods3 import get_data as get_ods_data


def _normalize_date_value(v):
    """Convert various date-like values to date string in DD/MM/YYYY when possible.
    Keeps previous fallback behavior for numeric and unparseable values.
    """
    if v is None:
        return None
    try:
        if isinstance(v, pd.Timestamp):
            return v.strftime("%d/%m/%Y")
    except Exception:
        pass
    try:
        if hasattr(v, 'strftime'):
            return v.strftime("%d/%m/%Y")
    except Exception:
        pass
    try:
        if isinstance(v, (int, float)):
            return str(v)
    except Exception:
        pass
    s = str(v).strip()
    return s if s != '' else None


def df_to_promo_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if df is None or df.shape[0] == 0:
        return rows

    # normalize column names -> original column object mapping
    col_map = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(' ', '_')
        col_map[key] = col

    def get_val(rec: Dict[str, Any], *variants: str):
        for v in variants:
            k = v.lower().replace(' ', '_')
            if k in col_map:
                return rec.get(col_map[k])
        return None

    for rec in df.to_dict(orient='records'):
        item_code = get_val(rec, 'Item code', 'item_code', 'code', 'item code')
        barcode = get_val(rec, 'Barcode', 'barcode')
        item_name = get_val(rec, 'Item name', 'item_name', 'name', 'item name')
        typ = get_val(rec, 'Type', 'type')
        # accept additional header variants that may appear in files (e.g. 'Promotion VN')
        name_promo = get_val(rec, 'Name promotion', 'name_promotion', 'promotion_name', 'name', 'promotion vn', 'promotion_vn', 'promotion_vietnam', 'promotion vn name', 'promotion_vn_name')
        start = get_val(rec, 'Start Date', 'start_date', 'start', ' start date')
        end = get_val(rec, 'End Date', 'end_date', 'end', ' end date')


        rows.append({
            'item_code': str(item_code).strip() if item_code is not None else None,
            'barcode': str(barcode).strip() if barcode is not None else None,
            'item_name': str(item_name).strip() if item_name is not None else None,
            'type': str(typ).strip() if typ is not None else None,
            'name_promotion': str(name_promo).strip() if name_promo is not None else None,
            'start_date': _normalize_date_value(start),
            'end_date': _normalize_date_value(end),
        })

    return rows


def row_to_promo_obj_by_headers(headers: List[str], row: List[Any]) -> Dict[str, Any]:
    d = {}
    for i, h in enumerate(headers):
        key = str(h).strip()
        val = None
        try:
            val = row[i]
        except Exception:
            val = None
        d[key] = val

    def pick(*names: str):
        for n in names:
            for k in d.keys():
                if k.strip().lower().replace(' ', '_') == n.strip().lower().replace(' ', '_'):
                    return d[k]
        return None

    item_code = pick('Item code', 'item_code', 'code', 'item code')
    barcode = pick('Barcode', 'barcode')
    item_name = pick('Item name', 'item_name', 'name', 'item name')
    typ = pick('Type', 'type')
    # accept 'Promotion VN' and similar header names as well
    name_promo = pick('Name promotion', 'name_promotion', 'promotion_name', 'name', 'promotion vn', 'promotion_vn', 'promotion_vietnam', 'promotion vn name', 'promotion_vn_name', 'vn','VN')
    start = pick('Start Date', 'start_date', 'start','start date')
    end = pick('End Date', 'end_date', 'end', 'end date')

    return {
        'item_code': str(item_code).strip() if item_code is not None else None,
        'barcode': str(barcode).strip() if barcode is not None else None,
        'item_name': str(item_name).strip() if item_name is not None else None,
        'type': str(typ).strip() if typ is not None else None,
        'name_promotion': str(name_promo).strip() if name_promo is not None else None,
        'start_date': _normalize_date_value(start),
        'end_date': _normalize_date_value(end),
    }


def parse_promotion_file(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """Parse given file into a list of promotion row dicts.

    Supports .xlsx/.xls/.xlsm (openpyxl), .xlsb (pyxlsb if available), and .ods (pyexcel_ods3).
    """
    ext = os.path.splitext(filename)[1].lower()
    parsed_rows: List[Dict[str, Any]] = []

    if ext in ('.xlsx', '.xls', '.xlsm'):
        df = pd.read_excel(file_path, engine='openpyxl')
        parsed_rows = df_to_promo_rows(df)

    elif ext == '.xlsb':
        try:
            df = pd.read_excel(file_path, engine='pyxlsb')
            parsed_rows = df_to_promo_rows(df)
        except Exception as exc:
            raise RuntimeError("xlsb parsing requires 'pyxlsb' package: " + str(exc))

    elif ext == '.ods':
        ods = get_ods_data(file_path)
        first_sheet = next(iter(ods.values())) if isinstance(ods, dict) and len(ods) > 0 else []
        if not first_sheet:
            parsed_rows = []
        else:
            headers = [str(h).strip() for h in first_sheet[0]]
            for row in first_sheet[1:]:
                parsed_rows.append(row_to_promo_obj_by_headers(headers, row))

    else:
        raise RuntimeError(f"Unsupported file extension: {ext}")

    return parsed_rows
