import random, requests, itertools, sys

# ---------- 1. Thu proxy free -------------
LIST_URLS = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/socks5.txt",
]

def fetch_proxies():
    proxies = set()
    for url in LIST_URLS:
        try:
            txt = requests.get(url, timeout=10).text
            proxies.update(line.strip() for line in txt.splitlines() if line.strip())
        except Exception as e:
            print(f"[WARN] Không lấy được {url}: {e}", file=sys.stderr)
    return list(proxies)

# ---------- 2. Kiểm tra proxy -------------
TEST_URL = "https://www.youtube.com"   # gọi trang chủ là đủ
TIMEOUT  = 5

def is_proxy_alive(proxy: str) -> bool:
    proxy_url = f"socks5://{proxy}"
    try:
        r = requests.get(
            TEST_URL, timeout=TIMEOUT,
            proxies={"http": proxy_url, "https": proxy_url},
            headers={"User-Agent": "Mozilla/5.0"}
        )
        return r.ok
    except Exception:
        return False

def pick_working_proxy(max_test=30):
    proxies = fetch_proxies()
    random.shuffle(proxies)
    for proxy in itertools.islice(proxies, max_test):     # thử N proxy đầu
        if is_proxy_alive(proxy):
            print("✓ Proxy Live:", proxy)
            return f"socks5://{proxy}"
        else:
            print("✗ Dead:", proxy)
    raise RuntimeError(f"Không tìm được proxy sống trong {max_test} proxy!")

proxy = pick_working_proxy()