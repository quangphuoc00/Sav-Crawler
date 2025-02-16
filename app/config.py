from typing import List, Dict

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "DNT": "1"
}

PROXY_AUTH = {
    'username': 'user-tekinno_obTwW',
    'password': '_ThoiDungHack123'
}

# Add this at the top with other constants
PROGRESS_DIR = "crawler_progress"

def get_progress_filepath(site_name: str) -> str:
    """Get the full path for a site's progress file"""
    return f"{PROGRESS_DIR}/crawler_progress_{site_name}.json"

# Update CRAWLER_COMMON to include progress directory
CRAWLER_COMMON = {
    "batch_size": 10,     # Number of pages to fetch in parallel before processing
    "min_delay": 2,       # Minimum delay between batches (in seconds)
    "max_delay": 4,       # Maximum delay between batches (in seconds)
    "save_interval": 100,  # Save progress every N SKUs processed
    "progress_dir": PROGRESS_DIR
}

# Site-specific configurations
CRAWLER_CONFIGS: Dict[str, dict] = {
    "cocowest": {
        "base_url": "https://cocowest.ca",
        "site_name": "cocowest",
        "sku_range": {
            "start": 1001,
            "end": 10000,
        },
        "warehouse_ids": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,107,108,109] # West
    },
    "cocoquebec": {
        "base_url": "https://cocoquebec.ca",
        "site_name": "cocoquebec",
        "sku_range": {
            "start": 1,
            "end": 10
        },
        "warehouse_ids":[84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106] # QBt
    },
    "cocoeast": {
        "base_url": "https://cocoeast.ca",
        "site_name": "cocoeast",
        "sku_range": {
            "start": 1,
            "end": 10
        },
        "warehouse_ids":[37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83]
    }
} 