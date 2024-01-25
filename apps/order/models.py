from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Form, HTTPException
from pydantic import BaseModel, Field, EmailStr
from pymongo import DESCENDING

from apps.coupons.models import get_coupon_by_id
from apps.product.models import ProductSchema
from db import db

ord_collection = db['order']
ord_it_collection = db['order_item']
ord_collection.create_index([("created", DESCENDING)])
product_collection = db['product']


class OrderItemSchema(BaseModel):
    product_id: str
    price: float
    quantity: int = Field(gt=0)
    product_name: str

    def get_cost(self):
        return Decimal(self.price) * self.quantity

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity']
                   for item in self.cart['items'].values())


class OrderItemCreateSchema(BaseModel):
    product: str
    quantity: int = Field(gt=0)

    @classmethod
    def as_form(
            cls,
            product: str = Form(...),
            quantity: int = Form(...),
    ):
        return cls(
            product=product,
            quantity=quantity,
        )


class OrderSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    address: str
    postal_code: str
    city: str
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)
    paid: bool = False
    stripe_id: Optional[str] = None
    stripe_url: Optional[str] = None
    items: list[OrderItemSchema]
    coupon: Optional[dict] = None
    discount: Optional[int] = None

    def get_total_cost_before_discount(self):
        return sum(item.get_cost() for item in self.items)

    def get_discount(self):
        total_cost = self.get_total_cost_before_discount()

        if self.discount:
            return total_cost * (self.discount / Decimal(100))
        return Decimal(0)

    def get_total_cost(self):
        total_cost = self.get_total_cost_before_discount()

        return total_cost - self.get_discount()


class OrderCreateSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    address: str
    postal_code: str
    city: str
    products: list[str]
    quantities: list[str]
    delete: Optional[List[str]] = Field(None)
    stripe_id: Optional[str] = Field(None)
    stripe_url: Optional[str] = Field(None)
    coupon: Optional[str] = Field(None)
    discount: Optional[int] = Field(None)
    paid: Optional[bool] = Field(False)

    @classmethod
    def as_form(
            cls,
            first_name: str = Form(...),
            last_name: str = Form(...),
            email: EmailStr = Form(...),
            address: str = Form(...),
            postal_code: str = Form(...),
            city: str = Form(...),
            products: list[str] = Form(...),
            quantities: list[str] = Form(...),
            delete: list[str] = Form(None),
            stripe_id: Optional[str] = Form(None),
            stripe_url: Optional[str] = Form(None),
            coupon: Optional[str] = Form(None),
            discount: Optional[int] = Form(None),
            paid: Optional[bool] = Form(False),
    ):
        return cls(
            first_name=first_name,
            last_name=last_name,
            email=email,
            address=address,
            postal_code=postal_code,
            city=city,
            products=products,
            quantities=quantities,
            delete=delete,
            stripe_id=stripe_id,
            stripe_url=stripe_url,
            coupon=coupon,
            discount=discount,
            paid=paid,
        )


def order_helper(order) -> dict:
    return {
        "_id": str(order["_id"]),
        "first_name": order["first_name"],
        "last_name": order["last_name"],
        "email": order["email"],
        "address": order["address"],
        "postal_code": order["postal_code"],
        "city": order["city"],
        "created": order["created"],
        "updated": order["updated"],
        "paid": order["paid"],
        "coupon": order.get("coupon"),
        "items": order["items"],
    }


def order_item_helper(order_item) -> dict:
    return {
        "_id": str(order_item["_id"]),
        "product_id": order_item["product_id"],
        "product_name": order_item["product_name"],
        "price": order_item["price"],
        "quantity": order_item["quantity"],
    }


async def create_order_item(item_data: dict):
    try:
        product = await product_collection.find_one({"_id": ObjectId(item_data['product_id'])})
        if product is None:
            raise HTTPException(status_code=422, detail="You must provide an existing product ID!")
        item_data['product_name'] = product["name"]
        item_data['quantity'] = int(item_data['quantity'])
        item_data['price'] = float(product['price'])
        new_order_item = await ord_it_collection.insert_one(item_data)
        created_order_item = await ord_it_collection.find_one({"_id": new_order_item.inserted_id})
        result = order_item_helper(created_order_item)
        return result
    except Exception as e:
        if isinstance(e, InvalidId):
            raise HTTPException(status_code=422, detail="You must provide an existing product ID!")
        raise e


async def create_order(order_data: dict, items: List[dict]):
    order_data["created"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    order_data["updated"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    order_data["paid"] = False
    order_data['items'] = [await create_order_item(item)
                           for item in items]

    for key in ['products', 'quantities', 'delete']:
        order_data.pop(key, None)

    if (coupon_data := order_data.get('coupon')) is not None:
        coupon = await get_coupon_by_id(coupon_data)
        order_data['coupon'] = coupon
        order_data['discount'] = coupon["discount"]
    new_order = await ord_collection.insert_one(order_data)
    created_order = await ord_collection.find_one({"_id": new_order.inserted_id})
    return order_helper(created_order)


async def edit_order(_id: str, order_data: dict):
    order_data["updated"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

    order_items = []

    for product_id, quantity in zip(order_data['products'], order_data['quantities']):
        if product_id.startswith("item_"):
            product_id = product_id[5:]
            if not order_data['delete'] or product_id not in order_data['delete']:
                await ord_it_collection.update_one({"_id": ObjectId(product_id)}, {"$set": {"quantity": int(quantity)}})
                item = await ord_it_collection.find_one({"_id": ObjectId(product_id)})
                order_items.append(order_item_helper(item))
        else:
            if not product_id:
                continue
            item = await create_order_item({"product_id": product_id, "quantity": quantity})
            order_items.append(item)

    if len(order_items) == 0:
        raise HTTPException(status_code=422, detail="You can't leave an order without order items!")

    order_data["items"] = order_items

    if order_data['delete']:
        for item_id in order_data['delete']:
            await ord_it_collection.delete_one({"_id": ObjectId(item_id)})

    for key in ['products', 'quantities', 'delete']:
        order_data.pop(key, None)

    if (coupon_data := order_data.get('coupon')) is not None:
        coupon = await get_coupon_by_id(coupon_data)
        order_data['coupon'] = coupon
        order_data['discount'] = coupon["discount"]

    await ord_collection.update_one({"_id": ObjectId(_id)}, {"$set": order_data})

    order = await get_order_by_id(_id)
    return order


async def get_order_by_id(_id: str):
    order = await ord_collection.find_one({"_id": ObjectId(_id)})
    if order:
        return order


async def get_order_items(items_data: list[dict]):
    items = []
    for item in items_data:
        i = OrderItemSchema(**item)
        i._id = item["_id"]
        items.append(i)
    return items


async def get_all_orders():
    orders = []
    async for order in ord_collection.find():
        o = OrderSchema(**order)
        o._id = str(order["_id"])
        orders.append(o)
    return orders
