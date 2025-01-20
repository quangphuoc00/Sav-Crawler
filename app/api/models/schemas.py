from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class PriceHistoryInput(BaseModel):
    date_posted: date
    savings: str
    expiry: date
    discounted_price: str

class ProductUpdateInput(BaseModel):
    name: str
    sku: int
    warehouse_ids: List[int]
    image_url: str
    price_history: List[PriceHistoryInput]

class ProductUpdateRequest(BaseModel):
    __root__: List[ProductUpdateInput] 