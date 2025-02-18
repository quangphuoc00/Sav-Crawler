import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
from typing import List
from app.utils import get_random_headers
import os
from collections import deque
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
import zipfile
import tempfile

VISITED_ARTICLES_FILE = "crawler_progress/visited_articles.txt"
MAX_STORED_URLS = 10

def load_visited_articles() -> deque:
    """Load previously visited article URLs from file"""
    try:
        os.makedirs(os.path.dirname(VISITED_ARTICLES_FILE), exist_ok=True)
        if os.path.exists(VISITED_ARTICLES_FILE):
            with open(VISITED_ARTICLES_FILE, 'r') as f:
                urls = f.read().splitlines()
                return deque(urls, maxlen=MAX_STORED_URLS)
        return deque(maxlen=MAX_STORED_URLS)
    except Exception as e:
        print(f"Error loading visited articles: {str(e)}")
        return deque(maxlen=MAX_STORED_URLS)

def save_visited_articles(visited_urls: deque):
    """Save visited article URLs to file"""
    try:
        with open(VISITED_ARTICLES_FILE, 'w') as f:
            f.write('\n'.join(visited_urls))
    except Exception as e:
        print(f"Error saving visited articles: {str(e)}")

def create_skus_zip(skus: List[int]) -> str:
    """Create a zip file containing SKUs and return its path"""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    txt_path = os.path.join(temp_dir, f'daily_sales_skus_{datetime.now().strftime("%Y%m%d")}.txt')
    zip_path = os.path.join(temp_dir, f'daily_sales_skus_{datetime.now().strftime("%Y%m%d")}.zip')
    
    # Write SKUs to text file
    with open(txt_path, 'w') as f:
        f.write('\n'.join(map(str, skus)))
    
    # Create zip file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(txt_path, os.path.basename(txt_path))
    
    return zip_path

def send_email_report(skus: List[int], articles_processed: int, error: str = None):
    """Send email report of daily sales scraping results"""
    try:
        sender_email = os.getenv('EMAIL_SENDER')
        sender_password = os.getenv('EMAIL_PASSWORD')
        receiver_email = os.getenv('EMAIL_RECEIVER')  # Sending to self
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"Daily Sales Crawler Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if error:
            body = f"❌ Daily Sales Crawler Failed\n\nError: {error}"
        else:
            body = f"""✅ Daily Sales Crawler Completed Successfully
            
Articles Processed: {articles_processed}
SKUs Found: {len(skus)}
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach zip file if there are SKUs
        if skus:
            zip_path = create_skus_zip(skus)
            with open(zip_path, 'rb') as f:
                zip_attachment = MIMEApplication(f.read(), _subtype='zip')
                zip_attachment.add_header('Content-Disposition', 'attachment', 
                                       filename=os.path.basename(zip_path))
                msg.attach(zip_attachment)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print("Email report sent successfully")
    except Exception as e:
        print(f"Failed to send email report: {str(e)}")

async def get_daily_sales_skus() -> List[int]:
    """Scrape SKUs from daily sales page on cocowest.ca"""
    try:
        all_skus = []
        visited_urls = load_visited_articles()
        
        # First get the main page to find the latest articles
        async with aiohttp.ClientSession() as session:
            async with session.get('https://cocowest.ca', headers=get_random_headers()) as response:
                if response.status != 200:
                    print(f"Failed to fetch main page: {response.status}")
                    return []
                
                main_html = await response.text()
                main_soup = BeautifulSoup(main_html, 'html.parser')
                
                # Get first 10 articles
                articles = main_soup.find_all('article')[:10]  # Only get first 10
                if not articles:
                    print("No articles found on main page")
                    return []

                # Process each article
                articles_processed = 0
                for article in articles:  # This will now only loop through max 10 articles
                    article_link = article.find('a')
                    if not article_link or not article_link.get('href'):
                        continue
                    
                    article_url = article_link['href']
                    
                    # Skip if we've already visited this URL
                    if article_url in visited_urls:
                        print(f"Skipping previously visited article: {article_url}")
                        continue
                    
                    articles_processed += 1
                    if articles_processed > 10:
                        break
                        
                    print(f"Processing article {articles_processed}: {article_url}")
                    
                    async with session.get(article_url, headers=get_random_headers()) as article_response:
                        if article_response.status != 200:
                            print(f"Failed to fetch article {articles_processed}: {article_response.status}")
                            continue
                        
                        article_html = await article_response.text()
                        article_soup = BeautifulSoup(article_html, 'html.parser')
                        
                        # Find all figcaptions
                        figcaptions = article_soup.find_all('figcaption', class_='wp-caption-text')
                        
                        article_skus = []
                        for figcaption in figcaptions:
                            # Extract any number from text using regex
                            text = figcaption.get_text()
                            match = re.search(r'\b\d+\b', text)
                            if match:
                                article_skus.append(int(match.group()))
                        
                        print(f"Found {len(article_skus)} SKUs from article {articles_processed}")
                        all_skus.extend(article_skus)
                        
                        # Add URL to visited list
                        visited_urls.append(article_url)

                # Save updated visited URLs
                save_visited_articles(visited_urls)

                print(f"Found total of {len(all_skus)} SKUs from {articles_processed} articles:")
                print(all_skus)
                
                # Send email report
                try:
                    send_email_report(all_skus, articles_processed)
                except Exception as e:
                    print(f"Failed to send email report, but continuing: {str(e)}")
                
                # Directly call discount crawler with found SKUs
                if all_skus:
                    from app.crawlers.discount_crawler import DiscountCrawler
                    from app.config import CRAWLER_CONFIGS, CRAWLER_COMMON
                    
                    config = CRAWLER_CONFIGS["cocowest"]
                    crawler = DiscountCrawler(
                        batch_size=CRAWLER_COMMON["batch_size"],
                        min_delay=CRAWLER_COMMON["min_delay"],
                        max_delay=CRAWLER_COMMON["max_delay"],
                        save_interval=CRAWLER_COMMON["save_interval"],
                        base_url=config["base_url"],
                        site_name=config["site_name"]
                    )
                    await crawler.scrape_found_skus(
                        warehouse_ids=config["warehouse_ids"],
                        skus=all_skus
                    )
                    print(f"Started discount crawler directly with {len(all_skus)} SKUs")
                
                return all_skus

    except Exception as e:
        error_msg = str(e)
        print(f"Error scraping daily sales: {error_msg}")
        # Send error report
        send_email_report([], 0, error=error_msg)
        return []

if __name__ == "__main__":
    asyncio.run(get_daily_sales_skus()) 