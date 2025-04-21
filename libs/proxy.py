import random, requests, itertools, sys
from concurrent.futures import ThreadPoolExecutor

# ---------- 1. Thu proxy free -------------
LIST_URLS = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",  # HTTP proxy
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",  # SOCKS5 proxy
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/socks5.txt",  # SOCKS5 proxy khác
    "https://www.proxy-list.download/api/v1/get?type=socks5",  # SOCKS5 từ nguồn khác
    "https://raw.githubusercontent.com/roosterkid/openproxy-list/master/SOCKS5.txt",  # Thêm 1 nguồn proxy nữa
]

def fetch_proxies():
    proxies = set()
    for url in LIST_URLS:
        try:
            txt = requests.get(url, timeout=10).text
            proxies.update(line.strip() for line in txt.splitlines() if line.strip())
        except Exception as e:
            print(f"[WARN] Không lấy được {url}: {e}", file=sys.stderr)
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

def pick_working_proxy(max_test=100):  # Tăng max_test lên 100
    proxies = fetch_proxies()
    random.shuffle(proxies)
    
    with ThreadPoolExecutor(max_workers=20) as executor:  # Tăng số workers để test nhanh hơn
        # Kiểm tra song song các proxy
        results = list(executor.map(is_proxy_alive, proxies[:max_test]))  # Giới hạn kiểm tra tối đa `max_test`
    
    # Tìm proxy sống đầu tiên
    for proxy, result in zip(proxies[:max_test], results):
        if result:
            print("✓ Proxy Live:", proxy)
            return f"socks5://{proxy}"
        else:
            print("✗ Dead:", proxy)
    
    raise RuntimeError(f"Không tìm được proxy sống trong {max_test} proxy!")

# Lấy proxy sống đầu tiên
proxy = pick_working_proxy(max_test=100)  # Thử tối đa 100 proxy