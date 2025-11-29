import os
import json
from datetime import datetime
from typing import Any, List, Dict, Optional

def remove_wishlist_code(
    code_to_remove: str,
    category: Optional[str] = None,
    file_path: str = os.path.join("Data", "WishlistData.json"),
) -> Dict[str, Any]:
    """
    Xóa item theo code hoặc theo (code, category) khỏi file wishlist.
    Nếu category là None thì xóa tất cả mục có cùng code.
    Nếu category được truyền thì chỉ xóa entry khớp chính xác cả code và category.
    """
    wishlist = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                wishlist = json.load(f)
                if not isinstance(wishlist, list):
                    wishlist = []
            except Exception:
                wishlist = []

    if category is None:
        # remove all entries that match the code
        new_wishlist = [item for item in wishlist if item.get("code") != code_to_remove]
    else:
        # remove only entries that match both code and category
        new_wishlist = [
            item
            for item in wishlist
            if not (
                item.get("code") == code_to_remove
                and (item.get("category") == category)
            )
        ]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(new_wishlist, f, ensure_ascii=False, indent=2)

    removed_count = len(wishlist) - len(new_wishlist)
    return {
        "message": "Removed",
        "code": code_to_remove,
        "category": category,
        "removed": removed_count,
        "count": len(new_wishlist),
    }

def save_json_to_file(data: Any, prefix: str = "response") -> Optional[str]:
    """Lưu JSON ra file ./saved_responses kèm timestamp"""
    try:
        os.makedirs("saved_responses", exist_ok=True)
        fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        path = os.path.join("saved_responses", fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path
    except Exception:
        return None

def get_wishlist_data(wishlist_path: str = os.path.join("Data", "WishlistData.json")) -> List[Dict[str, Any]]:
    wishlist_data = []
    if os.path.exists(wishlist_path):
        with open(wishlist_path, "r", encoding="utf-8") as f:
            wishlist_data = json.load(f)
    return wishlist_data

def save_wishlist_data(data: Any, wishlist_path: str = os.path.join("Data", "WishlistData.json")) -> Dict[str, Any]:
    os.makedirs("Data", exist_ok=True)
    wishlist = []
    if os.path.exists(wishlist_path):
        with open(wishlist_path, "r", encoding="utf-8") as f:
            try:
                wishlist = json.load(f)
                if not isinstance(wishlist, list):
                    wishlist = []
            except Exception:
                wishlist = []
    # Normalize helper
    def _normalize_entry(d: Dict[str, Any]) -> Dict[str, Any]:
        return {"code": d.get("code"), "category": d.get("category") if d.get("category") is not None else None}

    # If dict payload: overwrite any existing entries for the same code with the provided category
    if isinstance(data, dict) and "code" in data:
        entry = _normalize_entry(data)
        # Remove any existing entries for this code
        wishlist = [item for item in wishlist if item.get("code") != entry["code"]]
        # Append the new (single) entry
        wishlist.append(entry)
    elif isinstance(data, list):
        # For list payloads, we'll process each and keep the last occurrence per code
        incoming: Dict[str, Dict[str, Any]] = {}
        for d in data:
            if isinstance(d, dict) and "code" in d:
                entry = _normalize_entry(d)
                incoming[str(entry["code"])] = entry

        # Remove any existing entries that are present in incoming, then append the incoming ones
        incoming_codes = set(Object := [k for k in incoming.keys()])
        wishlist = [item for item in wishlist if str(item.get("code")) not in incoming_codes]
        # append incoming in their provided order
        for k in incoming:
            wishlist.append(incoming[k])
    with open(wishlist_path, "w", encoding="utf-8") as f:
        json.dump(wishlist, f, ensure_ascii=False, indent=2)
    return {"message": "Saved", "path": wishlist_path, "count": len(wishlist)}
