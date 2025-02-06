import aiohttp
import json
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from app.utils import get_random_headers

class WarehouseCrawler:
    def __init__(self):
        self.base_url = "https://www.costco.ca/WarehouseListByStateDisplayView"
        
    async def fetch_warehouses(self) -> Optional[List[Dict]]:
        """
        Fetches and parses the warehouse list from Costco's website.
        Returns the parsed warehouse list or None if failed.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    headers=get_random_headers(),
                    ssl=False
                ) as response:
                    if response.status != 200:
                        print(f"Failed to fetch warehouse list: {response.status}")
                        return None
                        
                    html_content = await response.text()
                    return self._extract_warehouse_data(html_content)
                    
        except Exception as e:
            print(f"Error fetching warehouse data: {str(e)}")
            return None

    def _extract_warehouse_data(self, html_content: str) -> Optional[List[Dict]]:
        """
        Extracts the warehouse list from the page source.
        Looks for the allWarehousesList variable and parses its JSON value.
        """
        try:
            # Look for the allWarehouseList variable assignment
            pattern = r'var\s+allWarehousesList\s*=\s*(\[.*?\]);'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if not match:
                print("Could not find warehouse list in page source")
                return None
                
            # Extract and parse the JSON data
            json_str = match.group(1)
            raw_warehouse_list = json.loads(json_str)
            
            # Merge all warehouseLists into a single array
            warehouse_list = []
            for state in raw_warehouse_list:
                warehouse_list.extend(state['warehouseList'])
            
            print(f"Successfully extracted {len(warehouse_list)} warehouses")
            return warehouse_list
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse warehouse JSON: {str(e)}")
            return None
        except Exception as e:
            print(f"Error extracting warehouse data: {str(e)}")
            return None 