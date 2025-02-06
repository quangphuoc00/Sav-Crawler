import os
import json
import aiohttp
import asyncio
import random
import time
from typing import List, Dict
from app.config import get_progress_filepath, DEFAULT_HEADERS, USER_AGENTS
from app.utils import get_random_headers, get_random_proxy, load_proxies
from bs4 import BeautifulSoup
import re

class DiscountCrawler:
    def __init__(self, base_url, batch_size, min_delay, max_delay, save_interval, site_name):
        self.base_url = base_url
        self.batch_size = batch_size
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.save_interval = save_interval
        self.site_name = site_name
        self.results = {}
        self.proxies = load_proxies()
        self.session_start_time = time.time()
        self.requests_count = 0
        self.api_url = os.getenv('API_URL', 'http://host.docker.internal:8080/api/products/update')
        self.items_to_update = []

    def _should_rotate_session(self) -> bool:
        """Determine if we should rotate the session based on time or request count"""
        session_age = time.time() - self.session_start_time
        return (session_age > random.uniform(1800, 3600) or  # 30-60 minutes
                self.requests_count > random.randint(80, 120))

    async def _update_products(self, warehouse_ids: List[int]) -> bool:
        """Update products via API"""
        if not self.items_to_update:
            return True

        # Prepare items for API
        items_for_api = []
        for item in self.items_to_update:
            # Extract SKU from URL and ensure it's a string
            sku = item["url"].split("/")[-1]
            
            # Ensure price history format is correct
            price_history = []
            for price in item["price_history"]:
                price_entry = {
                    "date_posted": price["date_posted"],
                    "savings": price["savings"].replace("OFF", "").strip(),  # Remove "OFF" and whitespace
                    "expiry": price["expiry"],
                    "discounted_price": price["discounted_price"]
                }
                price_history.append(price_entry)

            api_item = {
                "sku": int(sku),  # Convert string to integer
                "name": item["name"],
                "image_url": item.get("image_url", ""),  # Default to empty string if missing
                "warehouse_ids": warehouse_ids,
                "price_history": price_history
            }
            items_for_api.append(api_item)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=items_for_api,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_text = await response.text()
                    print(f"Response Status: {response.status}")
                    print(f"Response Body: {response_text}")
                    
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success"):
                            print(f"Successfully updated {len(items_for_api)} items")
                            self.items_to_update = []
                            return True
                    return False
        except Exception as e:
            print(f"Error updating products: {str(e)}")
            print(f"API URL being used: {self.api_url}")
            return False

    async def crawl_range(self, warehouse_ids: List[int], start: int = 1, end: int = 1000) -> None:
        start_time = time.time()
        processed = 0
        total = end - start + 1
        failed_skus = []

        resume_from, existing_failed = self.load_progress()
        failed_skus.extend(existing_failed)
        
        if resume_from > start:
            print(f"Resuming from SKU {resume_from + 1}")  # Log next SKU instead
            start = resume_from + 1  # Start from next SKU
            total = end - start + 1  # Recalculate total

        while start <= end:
            conn = aiohttp.TCPConnector(ssl=False, force_close=True)
            timeout = aiohttp.ClientTimeout(total=60, connect=20, sock_read=20)
            
            async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
                self.session_start_time = time.time()
                self.requests_count = 0
                
                tasks = []
                batch_size = random.randint(
                    max(1, self.batch_size - 2),
                    self.batch_size + 2
                )

                while len(tasks) < batch_size and start <= end:
                    if self._should_rotate_session():
                        break
                        
                    tasks.append(self.fetch_page(session, start))
                    start += 1
                    processed += 1
                    
                    if random.random() < 0.1:  # 10% chance to show progress
                        elapsed = time.time() - start_time
                        progress = (processed / total) * 100
                        eta = (elapsed / processed) * (total - processed)
                        print(f"Progress: {progress:.2f}% | SKU: {start} | ETA: {eta/60:.2f} minutes")

                if tasks:
                    try:
                        await asyncio.gather(*tasks)
                        # Add successfully parsed items to update buffer
                        self.items_to_update.extend([item for item in self.results.values() if item])
                    except Exception as e:
                        print(f"Batch failed: {str(e)}")
                        failed_skus.extend(range(start - len(tasks), start))
                    
                    # Update products if we've reached save_interval
                    if len(self.items_to_update) >= self.save_interval:
                        if not await self._update_products(warehouse_ids):
                            # If update fails, add SKUs to failed list
                            failed_skus.extend([int(item["url"].split("/")[-1]) for item in self.items_to_update])
                    
                    self.results = {}
                    await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))
                
                if random.random() < 0.1:  # 10% chance to save progress
                    self.save_progress(start, failed_skus)

        # Update any remaining items
        if self.items_to_update:
            if not await self._update_products(warehouse_ids):
                failed_skus.extend([int(item["url"].split("/")[-1]) for item in self.items_to_update])

        self.save_progress(end, failed_skus)
        print(f"Crawl completed! Processed {processed} SKUs in {(time.time() - start_time)/60:.2f} minutes")
        print(f"Failed SKUs: {len(failed_skus)}")

    async def fetch_page(self, session: aiohttp.ClientSession, sku: int):
        """Fetch a single product page and parse item information"""
        url = f"{self.base_url}/item/{sku}"
        headers = get_random_headers()
        proxy_config = get_random_proxy(self.proxies)
        
        max_retries = random.randint(2, 4)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.requests_count += 1
                
                async with session.get(url, headers=headers, **proxy_config, timeout=30) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        item_info = self._parse_item_page(html_content, sku)
                        if item_info:  # Only store if we successfully parsed information
                            self.results[str(sku)] = item_info
                        return
                    elif response.status == 429:
                        print(f"Rate limited on SKU {sku}, retrying with new proxy...")
                        proxy_config = get_random_proxy(self.proxies)
                    elif response.status in [403, 406, 408, 444]:
                        print(f"Possible bot detection (status {response.status}), rotating session...")
                        return
                    else:
                        print(f"Failed to fetch SKU {sku}: {response.status}")
                        return
                        
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                print(f"Connection error for SKU {sku}: {str(e)}")
                proxy_config = get_random_proxy(self.proxies)
            except Exception as e:
                print(f"Error fetching SKU {sku}: {str(e)}")
                if "proxy" in str(e).lower():
                    proxy_config = get_random_proxy(self.proxies)
                else:
                    return
            
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

    def _parse_item_page(self, html_content: str, sku: int) -> dict:
        """Parse item information from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Initialize product data with only url
            item_info = {
                "url": f"{self.base_url}/item/{sku}",
            }

            # Find the entry header
            header = soup.find('header', class_='entry-header')
            if not header:
                return None

            # Get product name from h2 tag and verify it contains SKU
            title = header.find('h2')
            if title and str(sku) in title.text:
                # Remove SKU and any leading/trailing whitespace from name
                item_info["name"] = title.text.replace(str(sku), '').strip()
            else:
                print(f"Product name not found for SKU {sku}")
                return None

            # Get product image from img tag in header
            image = header.find('img')
            if image:
                item_info["image_url"] = image.get('src')

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

            item_info["price_history"] = price_history
            print(f"Successfully parsed SKU {sku}: {item_info['name']}")  # Simple success message
            return item_info

        except Exception as e:
            print(f"Error parsing SKU {sku}: {str(e)}")
            return None

    def load_progress(self) -> tuple[int, list[int]]:
        """Load progress from file, returns (last_sku, failed_skus)"""
        filename = get_progress_filepath(self.site_name)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        try:
            with open(filename, "r") as f:
                progress = json.load(f)
                # Support both old and new format
                if "failed" in progress:
                    # Migrate old format to new format
                    failed_skus = progress["failed"]
                    return progress["last_sku"], failed_skus
                return progress["last_sku"], progress.get("upload_failed", []) + progress.get("parse_failed", [])
        except FileNotFoundError:
            return 0, []

    def save_progress(self, last_sku: int, failed_skus: list[int]):
        """Save progress to file"""
        filename = get_progress_filepath(self.site_name)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Separate failed SKUs into parse_failed and upload_failed
        parse_failed = []
        upload_failed = []
        
        for sku in failed_skus:
            if str(sku) in self.results:  # If we have results, it was parsed but upload failed
                upload_failed.append(sku)
            else:  # If no results, parsing failed
                parse_failed.append(sku)
        
        with open(filename, "w") as f:
            json.dump({
                "last_sku": last_sku,
                "parse_failed": parse_failed,
                "upload_failed": upload_failed
            }, f) 