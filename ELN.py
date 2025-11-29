import os
import requests
from urllib.parse import urlparse, parse_qs

# URL to fetch (adjust as needed)
url = "http://elearning.circlek.com.vn/mod/quiz/review.php?attempt=301418&cmid=679"

# headers and cookies
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Host": "elearning.circlek.com.vn",
    "Referer": "http://elearning.circlek.com.vn/mod/quiz/view.php?id=679",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
}

cookies = {
    "_ga": "GA1.3.1821488261.1759129718",
    "_ga_LE28S70VWP": "GS2.3.s1760500275$o22$g0$t1760500275$j60$l0$h0",
    "__utma": "204692610.1821488261.1759129718.1760500275.1760796955.29",
    "__utmz": "204692610.1760796955.29.29.utmcsr=v1.awingconnect.vn|utmccn=(referral)|utmcmd=referral|utmcct=/",
    "MoodleSession": "pi9359vc3e3fs05eagc0jed4m9"   # thay đổi nếu hết hạn
}

# extract cmid and attempt from URL query string
parsed = urlparse(url)
qs = parse_qs(parsed.query)
cmid = qs.get('cmid', [None])[0]
attempt = qs.get('attempt', [None])[0]

# gửi request
resp = requests.get(url, headers=headers, cookies=cookies)
print("STATUS:", resp.status_code)

# build output folder/filename
base_dir = 'reviews'
if cmid:
    out_dir = os.path.join(base_dir, str(cmid))
else:
    out_dir = os.path.join(base_dir, 'unknown')
os.makedirs(out_dir, exist_ok=True)

if cmid and attempt:
    fname = f"review_attempt_{attempt}_cmid_{cmid}.html"
elif cmid:
    fname = f"review_cmid_{cmid}.html"
else:
    fname = "review_unknown.html"

out_path = os.path.join(out_dir, fname)

# save HTML
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(resp.text)

print(f"Saved review to {out_path}")
