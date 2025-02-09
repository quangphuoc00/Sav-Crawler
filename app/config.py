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
        "warehouse_ids": ["1069","1076","1092","1112","1157","1217","1234","1270","1296","1381","152","153","154","155","156","1578","158","160","161","163","164","251","254","255","256","258","259","51","54","543","544","548","549","55","552","56","57","593","656"]
    },
    "cocoquebec": {
        "base_url": "https://cocoquebec.ca",
        "site_name": "cocoquebec",
        "sku_range": {
            "start": 1,
            "end": 10
        },
        "warehouse_ids":["1127","1186","1213","1359","1367","1446","1447","503","505","515","516","518","521","525","527","528","529","532","536","542","546","556","801"]
    },
    "cocoeast": {
        "base_url": "https://cocoeast.ca",
        "site_name": "cocoeast",
        "sku_range": {
            "start": 1,
            "end": 10
        },
        "warehouse_ids":["1055","1090","1105","1128","1168","1169","1248","1261","1263","1265","1273","1316","1324","1345","1362","1414","1436","151","159","1591","1619","162","1655","1669","252","253","257","510","512","519","524","526","530","531","533","534","535","537","540","541","545","547","551","591","592","595","802"]
    }
} 