import typing as t
import json

from GetAmountCost import get_multiple_price_cost


def normalize_writeoff_payload(data: dict) -> t.List[dict]:
    """
    Normalize incoming write-off payload into a list of items.

    Expected input shapes (examples):
      { "itemCodes": [...], "quantities": [...] }
      { "item_codes": [...], "qty": [...] }

    Returns list of { item_code: str | None, quantity: float | int | None }
    Raises ValueError if top-level arrays are invalid.
    """
    # Accept multiple key aliases
    item_codes = data.get("itemCodes") or data.get("item_codes") or data.get("items") or []
    quantities = data.get("quantities") or data.get("qty") or []

    if not isinstance(item_codes, list) or not isinstance(quantities, list):
        raise ValueError("`itemCodes` and `quantities` must be arrays")

    items: t.List[dict] = []
    for i, code in enumerate(item_codes):
        qty = quantities[i] if i < len(quantities) else None
        qv: t.Union[float, int, None, str]
        try:
            if qty is None or str(qty).strip() == "":
                qv = None
            elif isinstance(qty, (int, float)):
                qv = qty
            else:
                # support comma separators
                qv = float(str(qty).replace(",", ""))
        except Exception:
            # keep original string when parsing fails
            qv = str(qty)

        items.append({
            "item_code": str(code) if code is not None else None,
            "quantity": qv,
        })

    return items


def fetch_costs_for_items(item_codes: t.List[str]) -> t.List[dict]:
    """
    Call GetAmountCost.get_multiple_price_cost to retrieve pricing/cost info for a list of item codes.

    Returns a list of dicts as returned by GetAmountCost (parsed from JSON string).
    """
    if not item_codes:
        return []

    # get_multiple_price_cost returns a JSON string (json.dumps)
    raw = get_multiple_price_cost(item_codes)
    try:
        parsed = json.loads(raw)
    except Exception:
        # if parsing fails, return empty
        parsed = []

    # parsed is expected to be a list of objects with itemCode/baseOrderPrice
    return parsed

