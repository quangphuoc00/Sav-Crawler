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
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

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
        self.api_url = os.getenv('API_URL', 'http://host.docker.internal:8080') + '/api/products/update'
        self.items_to_update = []
        # Add ANSI color codes
        self.RED = '\033[91m'
        self.RESET = '\033[0m'
        
        # Generate unique filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = "../found_skus"  # Go up one directory from /app to project root
        
        try:
            print(f"Attempting to create/verify directory: {log_dir}")
            # Create directory if it doesn't exist
            os.makedirs(log_dir, mode=0o777, exist_ok=True)
            print(f"Directory status - exists: {os.path.exists(log_dir)}")
            
            # Create unique file for this run
            self.found_skus_file = os.path.join(log_dir, f"found_skus_{self.site_name}_{timestamp}.txt")
            print(f"Attempting to create file at: {self.found_skus_file}")
            
            # Create the file with full permissions
            with open(self.found_skus_file, "w") as f:
                f.write(f"# SKU Log File for {self.site_name}\n")
                f.write(f"# Created: {timestamp}\n")
            
            # Set file permissions
            os.chmod(self.found_skus_file, 0o666)
            
            print(f"Successfully created SKU log file: {os.path.abspath(self.found_skus_file)}")
            print(f"File exists: {os.path.exists(self.found_skus_file)}")
            print(f"File permissions: {oct(os.stat(self.found_skus_file).st_mode)[-3:]}")
            print(f"Directory contents: {os.listdir(log_dir)}")
            
        except Exception as e:
            print(f"{self.RED}Error with SKU log file: {str(e)}{self.RESET}")
            print(f"{self.RED}Current working directory: {os.getcwd()}{self.RESET}")
            print(f"{self.RED}Parent directory contents: {os.listdir('..')}{self.RESET}")
            raise
        
        # Add thread-safe print lock
        self.print_lock = threading.Lock()

        self.receiver_email = "tekinno.sw@gmail.com"
        self.sender_email = os.getenv('EMAIL_SENDER', 'ddqphuoc@gmail.com')
        self.email_password = os.getenv('EMAIL_PASSWORD')

    def _should_rotate_session(self) -> bool:
        """Determine if we should rotate the session based on time or request count"""
        session_age = time.time() - self.session_start_time
        return (session_age > random.uniform(1800, 3600) or  # 30-60 minutes
                self.requests_count > random.randint(80, 120))

    async def _update_products(self, warehouse_ids: List[int]) -> bool:
        """Update products via API"""
        if not self.items_to_update:
            return True

        print(f"\n[UPLOAD] Preparing to upload {len(self.items_to_update)} items to API...")

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
                    "savings": price["savings"].replace("OFF", "").strip(),
                    "expiry": price["expiry"],
                    "final_price": price["final_price"]
                }
                price_history.append(price_entry)

            api_item = {
                "sku": int(sku),
                "name": item["name"],
                "image_url": item.get("image_url", ""),
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
                    
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success"):
                            print(f"[UPLOAD] ✅ Successfully uploaded {len(items_for_api)} items")
                            self.items_to_update = []
                            return True
                    # Only print response details if upload failed
                    print(f"{self.RED}[UPLOAD] ❌ Failed to upload {len(items_for_api)} items{self.RESET}")
                    print(f"{self.RED}[UPLOAD] Response Status: {response.status}{self.RESET} | message: {response_text}{self.RESET}")
                    return False
        except Exception as e:
            print(f"{self.RED}[UPLOAD] ❌ Error uploading products: {str(e)}{self.RESET}")
            print(f"{self.RED}[UPLOAD] API URL being used: {self.api_url}{self.RESET}")
            return False

    async def send_email(self, subject: str, body: str):
        try:
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = self.receiver_email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.email_password)
                server.send_message(message)
                print(f"Email sent: {subject}")
        except Exception as e:
            print(f"{self.RED}Failed to send email: {str(e)}{self.RESET}")

    async def scan_sku_range(self, start: int = 1, end: int = 1000) -> None:
        """First phase: Scan SKU range to find valid products and save to file"""
        try:
            start_time = time.time()
            processed = 0
            total = end - start + 1
            failed_skus = []
            current_index = start

            while current_index <= end:
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

                    while len(tasks) < batch_size and current_index <= end:
                        if self._should_rotate_session():
                            break
                            
                        tasks.append(self.check_sku_exists(session, current_index))
                        current_index += 1
                        processed += 1
                        
                        if random.random() < 0.1:
                            elapsed = time.time() - start_time
                            progress = (processed / total) * 100
                            eta = (elapsed / processed) * (total - processed)
                            print(f"Scan Progress: {progress:.2f}% | SKU: {current_index-1} | ETA: {eta/60:.2f} minutes")

                    if tasks:
                        try:
                            await asyncio.gather(*tasks)
                        except Exception as e:
                            print(f"Batch failed: {str(e)}")
                            failed_skus.extend(range(current_index - len(tasks), current_index))
                        
                        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

            elapsed_time = (time.time() - start_time) / 60
            completion_message = (
                f"Scan completed!\n"
                f"Processed SKUs: {start} to {end}\n"
                f"Time taken: {elapsed_time:.2f} minutes\n"
                f"Failed SKUs: {len(failed_skus)}"
            )
            print(completion_message)
            await self.send_email(
                f"[SavAI-Crawler] Scan Completed - {self.site_name}",
                completion_message
            )

        except Exception as e:
            error_message = f"Error during scan: {str(e)}"
            print(f"{self.RED}{error_message}{self.RESET}")
            await self.send_email(
                f"[SavAI-Crawler] Scan Error - {self.site_name}",
                error_message
            )
            raise

    async def check_sku_exists(self, session: aiohttp.ClientSession, sku: int):
        """Check if a SKU exists and has valid title"""
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
                        soup = BeautifulSoup(html_content, 'html.parser')
                        header = soup.find('header', class_='entry-header')
                        
                        if header:
                            title = header.find('h2')
                            if title and str(sku) in title.text:
                                with open(self.found_skus_file, "a") as f:
                                    f.write(f"{sku}\n")
                                print(f"✅ Found valid SKU {sku}")
                            else:
                                print(f"❌ SKU {sku} exists but no valid title found")
                        else:
                            print(f"❌ SKU {sku} not found (no header)")
                        return
                    elif response.status == 429:
                        print(f"{self.RED}Rate limited on SKU {sku}, retrying with new proxy...{self.RESET}")
                        proxy_config = get_random_proxy(self.proxies)
                    elif response.status in [403, 406, 408, 444]:
                        print(f"{self.RED}Possible bot detection (status {response.status}), rotating session...{self.RESET}")
                        return
                    else:
                        print(f"❌ SKU {sku} not found (status {response.status})")
                        return
                        
            except Exception as e:
                print(f"{self.RED}Error checking SKU {sku}: {str(e)}{self.RESET}")
                if "proxy" in str(e).lower():
                    proxy_config = get_random_proxy(self.proxies)
                else:
                    return
            
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

    async def scrape_found_skus(self, warehouse_ids: List[int], skus: List[int]) -> None:
        """Second phase: Parse and upload data for found SKUs"""
        if not skus:
            print(f"{self.RED}No SKUs provided to scrape{self.RESET}")
            return

        try:
            start_time = time.time()
            processed = 0
            total = len(skus)
            failed_skus = []
            current_index = 0

            while current_index < total:
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

                    while len(tasks) < batch_size and current_index < total:
                        if self._should_rotate_session():
                            break
                            
                        sku = skus[current_index]
                        tasks.append(self.fetch_page(session, sku))
                        current_index += 1
                        processed += 1
                        
                        if random.random() < 0.1:
                            elapsed = time.time() - start_time
                            progress = (processed / total) * 100
                            eta = (elapsed / processed) * (total - processed)
                            print(f"Scrape Progress: {progress:.2f}% | SKU: {sku} | ETA: {eta/60:.2f} minutes")

                    if tasks:
                        try:
                            await asyncio.gather(*tasks)
                            self.items_to_update.extend([item for item in self.results.values() if item])
                        except Exception as e:
                            print(f"Batch failed: {str(e)}")
                            failed_skus.extend(skus[current_index - len(tasks):current_index])
                        
                        if len(self.items_to_update) >= self.save_interval:
                            if not await self._update_products(warehouse_ids):
                                failed_skus.extend([int(item["url"].split("/")[-1]) for item in self.items_to_update])
                        
                        self.results = {}
                        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))

            # Update any remaining items
            if self.items_to_update:
                if not await self._update_products(warehouse_ids):
                    failed_skus.extend([int(item["url"].split("/")[-1]) for item in self.items_to_update])

            elapsed_time = (time.time() - start_time) / 60
            completion_message = (
                f"Scrape completed!\n"
                f"Total SKUs processed: {len(skus)}\n"
                f"Time taken: {elapsed_time:.2f} minutes\n"
                f"Failed SKUs: {len(failed_skus)}"
            )
            print(completion_message)
            await self.send_email(
                f"[SavAI-Crawler] Scrape Completed - {self.site_name}",
                completion_message
            )

        except Exception as e:
            error_message = f"Error during scrape: {str(e)}"
            print(f"{self.RED}{error_message}{self.RESET}")
            await self.send_email(
                f"[SavAI-Crawler] Scrape Error - {self.site_name}",
                error_message
            )
            raise

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
                        print(f"{self.RED}Rate limited on SKU {sku}, retrying with new proxy...{self.RESET}")
                        proxy_config = get_random_proxy(self.proxies)
                    elif response.status in [403, 406, 408, 444]:
                        print(f"{self.RED}Possible bot detection (status {response.status}), rotating session...{self.RESET}")
                        return
                    else:
                        print(f"{self.RED}Failed to fetch SKU {sku}: {response.status}{self.RESET}")
                        return
                        
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                print(f"{self.RED}Connection error for SKU {sku}: {str(e)}{self.RESET}")
                proxy_config = get_random_proxy(self.proxies)
            except Exception as e:
                print(f"{self.RED}Error fetching SKU {sku}: {str(e)}{self.RESET}")
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
                print(f"{self.RED}Product name not found for SKU {sku}{self.RESET}")
                return None

            # Get product image from img tag in header
            image = header.find('img')
            if image:
                item_info["image_url"] = image.get('src')

            # Parse price history
            price_history = []
            content_div = soup.find('div', class_='coco-entry-summary')
            if content_div:
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

                        # Convert price string to float
                        price_str = divs[3].text.strip().replace('$', '').replace(',', '')
                        try:
                            final_price = float(price_str)
                        except ValueError:
                            print(f"{self.RED}Invalid price format for SKU {sku}: {price_str}{self.RESET}")
                            final_price = -1.0

                        price_entry = {
                            "date_posted": date_posted,
                            "savings": divs[1].text.strip(),
                            "expiry": divs[2].text.strip(),
                            "final_price": final_price
                        }
                        price_history.append(price_entry)

            item_info["price_history"] = price_history
            print(f"Successfully parsed SKU {sku}: {item_info['name']}")  # Simple success message
            return item_info

        except Exception as e:
            print(f"{self.RED}Error parsing SKU {sku}: {str(e)}{self.RESET}")
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