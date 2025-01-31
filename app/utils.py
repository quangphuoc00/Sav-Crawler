import json
import random
from typing import Dict, Any, List
import aiohttp
from .config import USER_AGENTS, DEFAULT_HEADERS, PROXY_AUTH

def get_random_headers() -> Dict[str, str]:
    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    return headers

def get_random_proxy(proxies: List[str]) -> Dict[str, Any]:
    proxy = random.choice(proxies)
    if proxy:
        proxy_auth = aiohttp.BasicAuth(PROXY_AUTH['username'], PROXY_AUTH['password'])
        return {"proxy": proxy, "proxy_auth": proxy_auth}
    return {}

def load_proxies() -> List[str]:
    try:
        with open("proxies.json", "r") as f:
            proxy_list = json.load(f)
            return [f"http://{proxy['entryPoint']}:{proxy['port']}" for proxy in proxy_list]
    except FileNotFoundError:
        print("Proxies.json not found, using direct connection")
        return [None]
    except Exception as e:
        print(f"Error loading proxies: {str(e)}, using direct connection")
        return [None]

def save_failed_products(failed_products: Dict[str, Any]) -> None:
    with open("failed_updated_products.json", 'w', encoding='utf-8') as f:
        json.dump(failed_products, f, indent=2, ensure_ascii=False) 