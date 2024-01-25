from bson import ObjectId
from fastapi import Request
from fastapi.templating import Jinja2Templates

from apps.cart.cart import CartManager
from apps.coupons.models import get_valid_coupon_by_id
from db import db

cart_collection = db['cart']


async def get_current_cart(request: Request):
    cart_id = request.cookies.get('cart_id')
    coupon_id = request.cookies.get('coupon_id')

    cart = await cart_collection.find_one({"_id": ObjectId(cart_id)}) if cart_id else None

    cart = cart or {'items': {}, 'coupon_id': coupon_id}

    if coupon_id and await get_valid_coupon_by_id(coupon_id):
        cart['coupon_id'] = coupon_id
    else:
        request.cookies.pop('coupon_id', None)

    return CartManager(cart)


templates = Jinja2Templates(directory="templates")
