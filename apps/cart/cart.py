from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, List

from bson import ObjectId
from fastapi.responses import Response

from apps.coupons.models import get_coupon_by_id
from db import db

product_collection = db['product']
cart_collection = db['cart']


class CartManager:
    def __init__(self, cart):
        self.cart = cart
        self.coupon_id = cart.get('coupon_id')
        self.coupon = None

    def __aiter__(self) -> AsyncGenerator:
        """
        Asynchronous iterator to iterate through the cart items with populated product details.
        """

        product_ids = list(self.cart['items'].keys())
        populated_cart_items = self._populate_cart_with_products(product_ids)

        return populated_cart_items

    def __len__(self):
        """
        Count all the items in the shopping cart.
        """

        return sum(item['quantity'] for item in self.cart['items'].values())

    @staticmethod
    async def _get_products(product_ids: List[str]):
        """
        Retrieve products from the database using List of product IDs.
        """
        products = await product_collection.find({'_id': {'$in': [ObjectId(_id) for _id in product_ids]}}).to_list(None)
        return products

    async def _populate_cart_with_products(self, product_ids: List[str]) -> AsyncGenerator:
        """
        Populate the cart with product details and yield cart items.
        """
        cart_copy = self.cart.copy()

        products = await self._get_products(product_ids)
        for product in products:
            product_id = str(product["_id"])
            cart_copy['items'][product_id]['product'] = product

        for item in cart_copy['items'].values():
            item['price'] = float(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            item['product_id'] = str(item['product']['_id'])

            yield item

    async def add(self, product_id: str, override_quantity: bool, quantity: int = 1) -> None:
        """
        Add a product to the cart.
        """
        product = await product_collection.find_one({"_id": ObjectId(product_id)})
        if product_id not in self.cart['items']:
            self.cart['items'][product_id] = {'quantity': 0,
                                              'price': str(product['price'])}

        if override_quantity:
            self.cart['items'][product_id]['quantity'] = quantity
        else:
            self.cart['items'][product_id]['quantity'] += quantity

    async def remove(self, product_id: str, redir_resp: Response) -> None:
        """
        Remove a product from the cart.
        """
        if product_id in self.cart['items']:
            del self.cart['items'][product_id]
            await self.save(redir_resp)

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity']
                   for item in self.cart['items'].values())

    async def save(self, response: Response):
        self.cart['expiration_time'] = datetime.utcnow() + timedelta(hours=1)
        if "_id" not in self.cart:
            result = await cart_collection.insert_one(self.cart)
            cart_id = str(result.inserted_id)
            response.set_cookie(key="cart_id", value=cart_id)
        else:
            await cart_collection.replace_one({"_id": self.cart["_id"]}, self.cart)

    async def clear(self):
        await cart_collection.delete_one({'_id': ObjectId(self.cart['_id'])})

    async def set_coupon(self):
        self.coupon = await get_coupon_by_id(self.coupon_id)

    def get_discount(self):
        coupon = self.coupon
        if coupon:
            return (coupon["discount"] / Decimal(100)) * self.get_total_price()

        return Decimal(0)

    def get_total_price_after_discount(self):
        return self.get_total_price() - self.get_discount()
