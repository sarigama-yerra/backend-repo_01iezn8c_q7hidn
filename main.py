import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem, User

app = FastAPI(title="E-Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "E-Commerce backend is running"}

# Public product endpoints
@app.get("/api/products")
def list_products(category: Optional[str] = None):
    try:
        filter_query = {"category": category} if category else {}
        products = get_documents("product", filter_query, limit=100)
        # Convert ObjectId to str safely
        for p in products:
            if "_id" in p:
                p["id"] = str(p.pop("_id"))
        return {"items": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

@app.post("/api/products")
def create_product(product: Product):
    try:
        inserted_id = create_document("product", product)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

# Simple cart model for checkout
class CheckoutItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int

class CheckoutRequest(BaseModel):
    customer_name: str
    customer_email: str
    customer_address: str
    items: List[CheckoutItem]

@app.post("/api/checkout")
def checkout(payload: CheckoutRequest):
    try:
        # Calculate totals
        subtotal = sum(i.price * i.quantity for i in payload.items)
        total = subtotal  # Extend with tax/shipping as needed

        order_items: List[OrderItem] = [
            OrderItem(
                product_id=i.product_id,
                title=i.title,
                price=i.price,
                quantity=i.quantity,
            ) for i in payload.items
        ]
        order = Order(
            customer_name=payload.customer_name,
            customer_email=payload.customer_email,
            customer_address=payload.customer_address,
            items=order_items,
            subtotal=subtotal,
            total=total,
            status="pending",
        )
        order_id = create_document("order", order)
        return {"order_id": order_id, "status": "created", "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
