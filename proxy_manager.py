# proxy_manager.py
import socks
import random

PROXY_LIST = []

def load_proxies_from_file(filepath: str):
    global PROXY_LIST
    with open(filepath, "r") as f:
        lines = f.readlines()
    PROXY_LIST = []

    for line in lines:
        parts = line.strip().split(",")
        if len(parts) == 2:
            host, port = parts
            PROXY_LIST.append((socks.SOCKS5, host, int(port), True, None, None))
        elif len(parts) == 4:
            host, port, user, pwd = parts
            PROXY_LIST.append((socks.SOCKS5, host, int(port), True, user, pwd))

def get_random_proxy():
    if not PROXY_LIST:
        return None
    return random.choice(PROXY_LIST)
  
