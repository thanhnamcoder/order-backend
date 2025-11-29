def resource_path(relative_path):
    import sys, os
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)


# Hàm lấy nhiều giá trị bất kỳ từ file user_login.json
def get_login_info(keys=None):
    import json, os
    login_path = resource_path("Data\\Login\\user_login.json")
    if not os.path.exists(login_path):
        print("Không tìm thấy file user_login.json. Vui lòng nhập thông tin đăng nhập từ giao diện.")
        return None if keys else {}
    with open(login_path, "r", encoding="utf-8") as f:
        login_data = json.load(f)
    if keys is None:
        return login_data
    if isinstance(keys, (list, tuple)):
        return tuple(login_data.get(k, "") for k in keys)
    return login_data.get(keys, "")