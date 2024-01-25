import os

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

client = AsyncIOMotorClient(os.environ.get('MONGODB_URL'))
db = client[os.environ.get('MONGODB_DB')]


# SOME COMMON OPERATIONS

async def delete_product_image(_id: str):
    product = await db["product"].find_one({"_id": ObjectId(_id)})
    image_path = product.get("image", "")
    path_in_static_dir = f'static/{image_path}'
    if image_path and os.path.exists(path_in_static_dir):
        os.remove(path_in_static_dir)


async def delete_object(_id: str, model: str):
    if model == 'product':
        await delete_product_image(_id)

    result = await db[model].delete_one({"_id": ObjectId(_id)})
    return result


async def delete_objects(delete: str, model: str):
    delete_list = eval(delete)
    if model == "category":
        await db["product"].delete_many({"category_id": {"$in": delete_list}})
    if model == "product":
        for _id in delete_list:
            await delete_product_image(_id)
    await db[model].delete_many({"_id": {"$in": [ObjectId(_id) for _id in delete_list]}})
