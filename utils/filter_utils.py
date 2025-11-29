def parse_list_param(val: str):
    """Chuyển query param dạng 'a,b,c' hoặc xuống dòng thành set()"""
    if not val:
        return set()
    parts = [p.strip() for p in val.replace('\n', ',').split(',')]
    return {p for p in parts if p}
