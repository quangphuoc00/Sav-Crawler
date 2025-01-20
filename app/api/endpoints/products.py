from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database

router = APIRouter(
    prefix="/api/products",
    tags=["products"]
)

@router.post("/update")
async def update_products(
    products: List[schemas.ProductUpdateInput],
    db: Session = Depends(database.get_db)
):
    try:
        for product in products:
            # Check if product exists
            db_product = db.query(models.ProductItem).filter(
                models.ProductItem.sku == product.sku
            ).first()
            
            # If product doesn't exist, create it
            if not db_product:
                db_product = models.ProductItem(
                    sku=product.sku,
                    name=product.name,
                    image_url=product.image_url,
                    warehouse_ids=product.warehouse_ids
                )
                db.add(db_product)
                db.flush()
            
            # Process price history
            for price in product.price_history:
                # Convert discounted_price string to float
                price_value = float(price.discounted_price.replace('$', ''))
                
                # Check if price history entry exists
                existing_price = db.query(models.PriceHistory).filter(
                    models.PriceHistory.item_sku == product.sku,
                    models.PriceHistory.date_posted == price.date_posted
                ).first()
                
                # Only add if date_posted doesn't exist
                if not existing_price:
                    new_price = models.PriceHistory(
                        item_sku=product.sku,
                        date_posted=price.date_posted,
                        savings=price.savings,
                        expiry=price.expiry,
                        final_price=price_value,
                        warehouse_ids=product.warehouse_ids
                    )
                    db.add(new_price)
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 