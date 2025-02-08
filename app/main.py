import asyncio
from app.crawlers.discount_crawler import DiscountCrawler
from app.config import CRAWLER_CONFIGS, CRAWLER_COMMON


async def run_crawler_scan(site: str, start: int, end: int):
    if site not in CRAWLER_CONFIGS:
        raise ValueError(f"No configuration found for site: {site}")
    
    config = CRAWLER_CONFIGS[site]
    
    # Initialize crawler with configuration from config.py
    crawler = DiscountCrawler(
        batch_size=CRAWLER_COMMON["batch_size"],
        min_delay=CRAWLER_COMMON["min_delay"],
        max_delay=CRAWLER_COMMON["max_delay"],
        save_interval=CRAWLER_COMMON["save_interval"],
        base_url=config["base_url"],
        site_name=config["site_name"]
    )
    
    # Start scanning using provided range
    await crawler.scan_sku_range(
        start=start,
        end=end
    )

async def run_crawler_scrape(site: str):
    if site not in CRAWLER_CONFIGS:
        raise ValueError(f"No configuration found for site: {site}")
    
    config = CRAWLER_CONFIGS[site]
    
    # Initialize crawler with configuration from config.py
    crawler = DiscountCrawler(
        batch_size=CRAWLER_COMMON["batch_size"],
        min_delay=CRAWLER_COMMON["min_delay"],
        max_delay=CRAWLER_COMMON["max_delay"],
        save_interval=CRAWLER_COMMON["save_interval"],
        base_url=config["base_url"],
        site_name=config["site_name"]
    )
    
    # Start scraping found SKUs
    await crawler.scrape_found_skus(
        warehouse_ids=config["warehouse_ids"]
    )

async def main():
    # Run scanner for cocowest
    print("Starting SKU scanning phase...")
    await run_crawler_scan("cocowest", start=10001, end=20000)
    
    # Run scraper for found SKUs
    # print("\nStarting SKU scraping phase...")
    # await run_crawler_scrape("cocowest")

if __name__ == "__main__":
    asyncio.run(main())
