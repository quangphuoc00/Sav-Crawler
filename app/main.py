import asyncio
from app.crawlers.discount_crawler import DiscountCrawler
from app.config import CRAWLER_CONFIGS, CRAWLER_COMMON


async def run_crawler(site: str):
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
    
    # Start crawling using configured range
    await crawler.crawl_range(
        warehouse_ids=config["warehouse_ids"],
        start=config["sku_range"]["start"],
        end=config["sku_range"]["end"]
    )

async def main():
    # Run crawler for cocowest
    await run_crawler("cocowest")

if __name__ == "__main__":
    asyncio.run(main())
