from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, UploadFile, Form, File
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING

from apps.category.models import CategorySchema
from db import db
from utils import create_slug, save_image, check_image_extension

cat_collection = db['category']
product_collection = db['product']
product_collection.create_index([("id", ASCENDING), ("slug", ASCENDING)])
product_collection.create_index([("name", ASCENDING)])
product_collection.create_index([("created_at", DESCENDING)])


class ProductSchema(BaseModel):
    category_id: str
    category_name: str
    name: str
    image: Optional[str] = Field(None, description="Image of the product")
    description: str
    price: float
    available: bool
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "category_id": "64bb6098a13688d244e7c759",
                "category_name": "Electronics",
                "name": "Product Name",
                "description": "Product description",
                "price": 10.99,
                "available": True,
            },
            "description": "A product representation",
            "notes": "This schema represents a product object with various fields."
        }


class ProductCreateSchema(BaseModel):
    category_id: str
    name: str
    image: UploadFile
    description: str
    price: float
    available: Optional[bool] = Field(False)

    @classmethod
    def as_form(
            cls,
            category_id: str = Form(...),
            name: str = Form(...),
            description: str = Form(...),
            price: float = Form(...),
            available: Optional[bool] = Form(False),
            image: UploadFile = File(...)
    ):
        return cls(
            category_id=category_id,
            name=name,
            image=image,
            description=description,
            price=price,
            available=available,
        )


def product_helper(product) -> dict:
    return {
        "_id": str(product["_id"]),
        "category_id": product["category_id"],
        "category_name": product["category_name"],
        "name": product["name"],
        "slug": product["slug"],
        "image": product["image"],
        "description": product["description"],
        "price": product["price"],
        "available": product["available"],
        "created": product["created"],
        "updated": product["updated"],
    }


async def create_product(product_data: dict):
    category = await cat_collection.find_one({"_id": ObjectId(product_data["category_id"])})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    product_data["category_name"] = category["name"]

    slug = create_slug(product_data["name"])

    if product_data['image'].size != 0:
        check_image_extension(product_data['image'])
        image_path = await save_image(slug, product_data['image'].file.read())
    else:
        image_path = None

    product_data["slug"] = slug
    product_data['available'] = True
    product_data["image"] = image_path
    product_data["created"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    product_data["updated"] = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

    new_product = await product_collection.insert_one(product_data)
    created_product = await product_collection.find_one({"_id": new_product.inserted_id})

    return product_helper(created_product)


async def edit_product(_id: str, data: dict):
    category = await cat_collection.find_one({"_id": ObjectId(data["category_id"])})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    data["category_name"] = category["name"]

    slug = create_slug(data['name'])

    if data['image'].filename:
        check_image_extension(data['image'])
        image_path = await save_image(slug, data['image'].file.read())
        data["image"] = image_path
    else:
        del data['image']

    data['slug'] = slug
    data["updated"] = datetime.utcnow()
    await product_collection.update_one({"_id": ObjectId(_id)}, {"$set": data})
    product = await get_product_by_id(_id)
    return product


async def get_all_products():
    products = []
    async for product in product_collection.find():
        products.append(product_helper(product))
    return products


async def get_available_products():
    products = []
    async for product in product_collection.find({"available": True}):
        products.append(product_helper(product))
    return products


async def get_products_by_category(category: CategorySchema):
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    products = []
    async for product in product_collection.find({"category_id": category["_id"], "available": True}):
        products.append(product_helper(product))
    return products


async def get_product_by_slug(_id: ObjectId, slug: str):
    product = await product_collection.find_one({"_id": ObjectId(_id), "slug": slug})
    if product:
        return product


async def get_product_by_id(_id: str):
    product = await product_collection.find_one({"_id": ObjectId(_id)})
    if product:
        return product
