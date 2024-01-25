import os
import time

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from apps.auth.routers import router as auth_router
from apps.cart.routers import router as cart_router
from apps.category.routers import router as cat_router
from apps.order.routers import router as order_router
from apps.payment.routers import router as payment_router
from apps.product.routers import router as product_router
from apps.coupons.routers import router as coupon_router
from apps.admin.routers import router as admin_router
from middleware import AdminMiddleware
from dotenv import load_dotenv
from db import db

user_collection = db['user']
load_dotenv()

# waiting for DB
while True:
    try:
        user_collection.insert_one({'username': os.environ.get('SUPERUSER_USERNAME'),
                                    'password': os.environ.get('SUPERUSER_PASSWORD')})
        break
    except Exception:
        time.sleep(3)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cat_router, tags=["Category"], prefix="/category")
app.include_router(product_router, tags=["Product"], prefix="/product")
app.include_router(cart_router, tags=["Cart"], prefix="/cart")
app.include_router(order_router, tags=["Order"], prefix="/order")
app.include_router(payment_router, tags=["Payment"], prefix="/payment")
app.include_router(auth_router, tags=["Auth"], prefix="/user")
app.include_router(coupon_router, tags=["Coupon"], prefix="/coupon")
app.include_router(admin_router, tags=["Admin"], prefix="/admin")

app.add_middleware(AdminMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    if 'email' in exc.errors()[0]['loc']:
        error_msg = exc.errors()[0]['ctx']['reason']
        response = RedirectResponse(url=request.url, status_code=303)
        response.set_cookie('error_msg', error_msg)
        return response


@app.get("/")
async def root():
    return RedirectResponse(url="/product", status_code=303)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
