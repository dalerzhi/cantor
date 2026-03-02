from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import datetime

app = FastAPI(title="Cantor Billing API")

# In-memory mock DB for orders
orders_db = {}

class CreateOrderRequest(BaseModel):
    tenant_id: str
    plan: str
    amount: float

class PaymentWebhookRequest(BaseModel):
    order_id: str
    status: str
    transaction_id: str

class Order(BaseModel):
    id: str
    tenant_id: str
    plan: str
    amount: float
    status: str
    created_at: str

@app.post("/api/orders", response_model=Order)
async def create_order(req: CreateOrderRequest):
    order_id = f"ord_{uuid.uuid4().hex[:8]}"
    order = Order(
        id=order_id,
        tenant_id=req.tenant_id,
        plan=req.plan,
        amount=req.amount,
        status="pending",
        created_at=datetime.datetime.utcnow().isoformat()
    )
    orders_db[order_id] = order
    return order

@app.post("/api/webhooks/payment")
async def handle_payment_webhook(req: PaymentWebhookRequest):
    if req.order_id not in orders_db:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order = orders_db[req.order_id]
    
    if req.status == "success":
        order.status = "paid"
        
        # 调用 cantor-gateway 的 Admin API 升级租户
        gateway_admin_url = "http://localhost:8766/admin/tenant/update"
        payload = {
            "tenant_id": order.tenant_id,
            "plan_tier": "standard",
            "status": "active"
        }
        
        try:
            import httpx
            # Async HTTP call to update tenant
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    gateway_admin_url, 
                    json=payload, 
                    headers={"Authorization": "Bearer admin-secret-token"},
                    timeout=5.0
                )
                if resp.status_code == 200:
                    print(f"✅ Payment successful for order {order.id}. Upgraded tenant {order.tenant_id} to {order.plan}.")
                else:
                    print(f"⚠️ Payment logged but gateway update failed: {resp.text}")
        except Exception as e:
            print(f"⚠️ Failed to call gateway admin API: {str(e)}")
        
    elif req.status == "failed":
        order.status = "failed"
        print(f"❌ Payment failed for order {order.id}.")
        
    return {"status": "ok", "order_status": order.status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
