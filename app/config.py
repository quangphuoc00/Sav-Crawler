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
    'username': 'user-savai_AElUv',
    'password': '_ThoiDungHack123'
}

# Add this at the top with other constants
PROGRESS_DIR = "crawler_progress"

def get_progress_filepath(site_name: str) -> str:
    """Get the full path for a site's progress file"""
    return f"{PROGRESS_DIR}/crawler_progress_{site_name}.json"

# Update CRAWLER_COMMON to include progress directory
CRAWLER_COMMON = {
    "batch_size": 2,     # Number of pages to fetch in parallel before processing
    "min_delay": 1,       # Minimum delay between batches (in seconds)
    "max_delay": 5,       # Maximum delay between batches (in seconds)
    "save_interval": 2,  # Save progress every N SKUs processed
    "progress_dir": PROGRESS_DIR
}

# Site-specific configurations
CRAWLER_CONFIGS: Dict[str, dict] = {
    "cocowest": {
        "base_url": "https://cocowest.ca",
        "site_name": "cocowest",
        "sku_range": {
            "start": 1835390,
            "end": 1835400,
        },
        "warehouse_ids": [3, 4, 5]
    },
    "cocoquebec": {
        "base_url": "https://cocoquebec.ca",
        "site_name": "cocoquebec",
        "sku_range": {
            "start": 1,
            "end": 10
        },
        "warehouse_ids": [0, 1, 2]
    },
    "cocoeast": {
        "base_url": "https://cocoeast.ca",
        "site_name": "cocoeast",
        "sku_range": {
            "start": 1,
            "end": 10
        },
        "warehouse_ids": [6, 7, 8]
    }
} 