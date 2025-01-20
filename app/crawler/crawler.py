import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
from typing import Dict, Any, List
import time
import random

class CocowestCrawler:
    def __init__(self):
        self.base_url = "https://cocowest.ca/item/{}"
        self.results: Dict[str, Any] = {}
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # Load proxies from Proxies.json
        try:
            with open("Proxies.json", "r") as f:
                proxy_list = json.load(f)
                self.proxies = [f"http://{proxy['entryPoint']}:{proxy['port']}" for proxy in proxy_list]
        except FileNotFoundError:
            print("Proxies.json not found, using direct connection")
            self.proxies = [None]
        except Exception as e:
            print(f"Error loading proxies: {str(e)}, using direct connection")
            self.proxies = [None]

        self.save_interval = 1000
        self.retry_attempts = 3
        self.retry_delay = 5
        self.batch_size = 8
        self.min_delay = 2
        self.max_delay = 10
        self.batch_delay = random.uniform(self.min_delay, self.max_delay)

    def get_random_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(self.user_agents),
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

    def get_random_proxy(self) -> Dict[str, str]:
        proxy = random.choice(self.proxies)
        if proxy:
            # Add Oxylabs proxy authentication
            proxy_auth = aiohttp.BasicAuth('user-savai_AElUv', '_ThoiDungHack123')
            return {"proxy": proxy, "proxy_auth": proxy_auth}
        return {}

    def generate_sku_range(self, start: int, end: int) -> List[int]:
        """Generate SKUs in random order within the range"""
        skus = list(range(start, end + 1))
        random.shuffle(skus)
        return skus

    def load_progress(self) -> int:
        try:
            with open("crawler_progress.json", "r") as f:
                progress = json.load(f)
                self.results = progress["results"]
                return progress["last_sku"]
        except FileNotFoundError:
            return 0

    def save_progress(self, last_sku: int):
        with open("crawler_progress.json", "w") as f:
            json.dump({"last_sku": last_sku, "results": self.results}, f)
        
        # Also save to products.json as backup
        self.save_results()

    async def fetch_page(self, session: aiohttp.ClientSession, sku: int) -> None:
        url = self.base_url.format(sku)
        headers = self.get_random_headers()
        proxy_settings = self.get_random_proxy()
        
        for attempt in range(self.retry_attempts):
            try:
                # Random small delay before each request
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                async with session.get(url, headers=headers, **proxy_settings) as response:
                    if response.status == 200:
                        html = await response.text()
                        await self.parse_product(html, sku)
                        return
                    elif response.status == 429:  # Too Many Requests
                        wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"Rate limited on SKU {sku}, waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"Failed to fetch SKU {sku}: Status {response.status}")
            except Exception as e:
                print(f"Error fetching SKU {sku} (attempt {attempt + 1}/{self.retry_attempts}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))

    async def parse_product(self, html: str, sku: int) -> None:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Initialize product data with only url
        product_data = {
            "url": self.base_url.format(sku),
        }

        # Find the entry header
        header = soup.find('header', class_='entry-header')
        if not header:
            print(f"Product not found for SKU {sku}")
            return

        # Get product name from h2 tag and verify it contains SKU
        title = header.find('h2')
        if title and str(sku) in title.text:
            # Remove SKU and any leading/trailing whitespace from name
            product_data["name"] = title.text.replace(str(sku), '').strip()
        else:
            print(f"Product name not found for SKU {sku}")
            return

        # Get product image from img tag in header
        image = header.find('img')
        if image:
            product_data["image_url"] = image.get('src')

        # Parse price history
        price_history = []
        content_div = soup.find('div', class_='coco-entry-summary')
        if content_div:
            # Find all flex rows except the header row
            price_rows = content_div.find_all('div', style=lambda x: x and 'flex-flow: row wrap' in x)
            for row in price_rows[1:]:  # Skip the header row
                divs = row.find_all('div', recursive=False)
                if len(divs) >= 4:
                    date_posted = None
                    date_link = divs[0].find('a')
                    if date_link:
                        date_posted = date_link.text.strip()
                    else:
                        date_posted = divs[0].text.strip()

                    price_entry = {
                        "date_posted": date_posted,
                        "savings": divs[1].text.strip(),
                        "expiry": divs[2].text.strip(),
                        "discounted_price": divs[3].text.strip()
                    }
                    price_history.append(price_entry)

        product_data["price_history"] = price_history
        self.results[str(sku)] = product_data
        print(f"Successfully scraped SKU {sku}: {product_data['name']}")

    async def crawl_range(self, start: int = 1, end: int = 1000) -> None:
        start_time = time.time()
        processed = 0
        total = end - start + 1

        # Load progress if exists
        resume_from = self.load_progress()
        if resume_from > start:
            print(f"Resuming from SKU {resume_from}")
            start = resume_from

        # Generate randomized SKU range
        skus = self.generate_sku_range(start, end)

        async with aiohttp.ClientSession() as session:
            tasks = []
            for sku in skus:
                tasks.append(self.fetch_page(session, sku))
                processed += 1
                
                # Progress tracking with randomized interval
                if processed % random.randint(90, 110) == 0:
                    elapsed = time.time() - start_time
                    progress = (processed / total) * 100
                    eta = (elapsed / processed) * (total - processed)
                    print(f"Progress: {progress:.2f}% | SKU: {sku} | ETA: {eta/60:.2f} minutes")

                # Batch processing with random sizes
                if len(tasks) >= random.randint(self.batch_size-2, self.batch_size+2):
                    await asyncio.gather(*tasks)
                    tasks = []
                    # Random delay between batches
                    self.batch_delay = random.uniform(self.min_delay, self.max_delay)
                    await asyncio.sleep(self.batch_delay)
                
                # Periodic saving with slight randomization
                if processed % (self.save_interval + random.randint(-50, 50)) == 0:
                    self.save_progress(sku)
                    print(f"Progress saved at SKU {sku}")
            
            if tasks:  # Process remaining tasks
                await asyncio.gather(*tasks)

        # Final save
        self.save_progress(end)
        print(f"Crawl completed! Processed {processed} SKUs in {(time.time() - start_time)/60:.2f} minutes")

    def save_results(self, filename: str = "products.json") -> None:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

async def main():
    crawler = CocowestCrawler()
    await crawler.crawl_range(534656, 534656)  # Full range
    crawler.save_results("products.json")

if __name__ == "__main__":
    asyncio.run(main()) 