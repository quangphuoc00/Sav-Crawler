from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, ARRAY, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProductItem(Base):
    __tablename__ = "product_item"
    
    sku = Column(Integer, primary_key=True)
    name = Column(String)
    image_url = Column(String)
    warehouse_ids = Column(ARRAY(Integer))

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    item_sku = Column(Integer, ForeignKey("product_item.sku"))
    date_posted = Column(Date)
    savings = Column(String)
    expiry = Column(Date)
    final_price = Column(Float)
    warehouse_ids = Column(ARRAY(Integer))
    
    __table_args__ = (
        UniqueConstraint('item_sku', 'date_posted', name='unique_item_date'),
    ) 