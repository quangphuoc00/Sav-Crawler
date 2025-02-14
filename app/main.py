import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from app.crawlers.discount_crawler import DiscountCrawler
from app.config import CRAWLER_CONFIGS, CRAWLER_COMMON
import os

app = FastAPI()

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
        found_skus_dir = "app/found_skus"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
