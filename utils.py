import os
from typing import Any

from bson import ObjectId
from fastapi import Request, Query, HTTPException

from math import ceil


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


def create_slug(name):
    return name.lower().replace(" ", "-")


async def save_image(product_slug: str, file: bytes):
    image_path_static = f"img/{product_slug}.png"

    with open(f'static/{image_path_static}', "wb") as image:
        image.write(file)

    return image_path_static


def get_value_from_cookies(request: Request, cookie_name: str) -> Any:
    return request.cookies.get(cookie_name)


def get_stripe_url(stripe_id):
    if '_test_' in os.environ.get('STRIPE_SECRET_KEY'):
        path = '/test/'
    else:
        path = '/'
    return f'https://dashboard.stripe.com{path}payments/{stripe_id}'


class Message:

    def __init__(self, text, tags='danger'):
        self.text = text
        self.tags = tags

    def __str__(self):
        return self.text


class Paginator:

    def __init__(self, getter):
        self.page = 0
        self.per_page = 0
        self.amount = 0
        self.start = 0
        self.end = 0
        self.last = 0
        self.next = 0
        self.previous = 0
        self.page_range = None
        self.getter = getter

    async def eval(self):
        objects = await self.getter()

        self.amount = len(objects)
        self.start = (self.page - 1) * self.per_page
        self.end = self.start + self.per_page
        self.last = ceil(self.amount / self.per_page)
        self.next = self.page + 1 if self.page != self.last else None
        self.previous = self.page - 1 if self.page > 1 else None
        self.page_range = range(1, self.last + 1)

    async def __call__(self, page: int = Query(1, gt=0), per_page: int = Query(10, gt=0)):
        self.page = int(page)
        self.per_page = int(per_page)
        await self.eval()
        return self


def check_image_extension(image):
    file_extension = image.filename.split(".")[-1]
    if file_extension not in ["png", "jpg"]:
        raise HTTPException(status_code=400, detail="Image file must be in PNG of JPG format")
