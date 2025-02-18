import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from app.crawlers.discount_crawler import DiscountCrawler
from app.config import CRAWLER_CONFIGS, CRAWLER_COMMON
import os
from app.crawlers.daily_sales import get_daily_sales_skus
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.add_job(run_daily_sales, 
                     trigger=CronTrigger(hour='9,17', 
                                       timezone='America/Vancouver'))
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
scheduler = AsyncIOScheduler()

class ScrapeRequest(BaseModel):
    site: str
    skus: List[int]

class ScrapeResponse(BaseModel):
    success: bool
    reason: str = ""

class ScanRequest(BaseModel):
    site: str
    start: int
    end: int

class FoundSkusResponse(BaseModel):
    skus: List[int]
    count: int

@app.post("/api/scrape", response_model=ScrapeResponse)
async def scrape_skus(request: ScrapeRequest):
    try:
        if request.site not in CRAWLER_CONFIGS:
            raise ValueError(f"No configuration found for site: {request.site}")
        
        if not request.skus:
            raise ValueError("No SKUs provided")
            
        config = CRAWLER_CONFIGS[request.site]
        
        # Initialize crawler with configuration
        crawler = DiscountCrawler(
            batch_size=CRAWLER_COMMON["batch_size"],
            min_delay=CRAWLER_COMMON["min_delay"],
            max_delay=CRAWLER_COMMON["max_delay"],
            save_interval=CRAWLER_COMMON["save_interval"],
            base_url=config["base_url"],
            site_name=config["site_name"]
        )
        
        scraping_task = asyncio.create_task(crawler.scrape_found_skus(
            warehouse_ids=config["warehouse_ids"],
            skus=request.skus
        ))
        
        return ScrapeResponse(success=True, reason="Scrape started in background")
        
    except ValueError as e:
        return ScrapeResponse(success=False, reason=str(e))
    except Exception as e:
        return ScrapeResponse(success=False, reason=f"Unexpected error: {str(e)}")

@app.post("/api/scan", response_model=ScrapeResponse)
async def scan_sku_range(request: ScanRequest):
    try:
        if request.site not in CRAWLER_CONFIGS:
            raise ValueError(f"No configuration found for site: {request.site}")
        
        if request.start > request.end:
            raise ValueError("Start value must be less than end value")
            
        config = CRAWLER_CONFIGS[request.site]
        
        crawler = DiscountCrawler(
            batch_size=CRAWLER_COMMON["batch_size"],
            min_delay=CRAWLER_COMMON["min_delay"],
            max_delay=CRAWLER_COMMON["max_delay"],
            save_interval=CRAWLER_COMMON["save_interval"],
            base_url=config["base_url"],
            site_name=config["site_name"]
        )
        
        scanning_task = asyncio.create_task(crawler.scan_sku_range(
            start=request.start,
            end=request.end
        ))
        
        return ScrapeResponse(success=True, reason="Scan started in background")
        
    except ValueError as e:
        return ScrapeResponse(success=False, reason=str(e))
    except Exception as e:
        return ScrapeResponse(success=False, reason=f"Unexpected error: {str(e)}")

@app.get("/api/found-skus", response_model=FoundSkusResponse)
async def get_found_skus():
    try:
        found_skus_dir = "../found_skus"
        # Create directory if it doesn't exist
        os.makedirs(found_skus_dir, exist_ok=True)
        
        all_skus = set()
        # Read all txt files in the directory
        for filename in os.listdir(found_skus_dir):
            if filename.endswith('.txt'):
                file_path = os.path.join(found_skus_dir, filename)
                with open(file_path, "r") as f:
                    # Read lines, convert to integers, and add to set
                    file_skus = {int(line.strip()) for line in f if line.strip()}
                    all_skus.update(file_skus)
        
        # Convert set to sorted list
        sorted_skus = sorted(all_skus)
        return FoundSkusResponse(skus=sorted_skus, count=len(sorted_skus))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_daily_sales():
    """Background task to run daily sales crawler"""
    try:
        print(f"Starting scheduled daily sales crawler at {datetime.now()}")
        skus = await get_daily_sales_skus()
        print(f"Scheduled daily sales crawler completed. Found {len(skus)} SKUs")
    except Exception as e:
        print(f"Error in scheduled daily sales crawler: {str(e)}")

@app.get("/api/daily-sales", response_model=FoundSkusResponse)
async def get_daily_sales_endpoint(background_tasks: BackgroundTasks):
    """Get SKUs from today's sales post"""
    try:
        # Run in background to avoid blocking
        background_tasks.add_task(run_daily_sales)
        return FoundSkusResponse(skus=[], count=0)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
