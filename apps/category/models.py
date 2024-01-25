from bson import ObjectId
from fastapi import Form
from pydantic import BaseModel
from pymongo import ASCENDING

from db import db
from utils import create_slug

cat_collection = db['category']
product_collection = db['product']
cat_collection.create_index([("name", ASCENDING)])
cat_collection.create_index([("slug", ASCENDING)], unique=True)


class CategorySchema(BaseModel):
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Category Name"
            },
            "description": "A category representation",
            "notes": "This schema represents a category object with name field."
        }


class CategoryCreateSchema(BaseModel):
    name: str

    @classmethod
    def as_form(cls, name: str = Form(...), ):
        return cls(name=name, )


def category_helper(category) -> dict:
    return {
        "_id": str(category["_id"]),
        "name": category["name"],
        "slug": category["slug"],
    }


async def create_category(category_data: dict):
    category_data["slug"] = create_slug(category_data['name'])
    new_category = await cat_collection.insert_one(category_data)
    created_category = await cat_collection.find_one({"_id": new_category.inserted_id})
    return category_helper(created_category)


async def edit_category(_id: str, data: dict):
    data['slug'] = create_slug(data['name'])
    await cat_collection.update_one({"_id": ObjectId(_id)}, {"$set": data})
    category = await get_category_by_id(_id)
    return category


async def get_all_categories():
    categories = []
    async for category in cat_collection.find():
        categories.append(category_helper(category))
    return categories


async def get_category_by_slug(slug: str):
    category = await cat_collection.find_one({"slug": slug})
    if category:
        return category_helper(category)


async def get_category_by_id(_id: str):
    category = await cat_collection.find_one({"_id": ObjectId(_id)})
    if category:
        return category_helper(category)

