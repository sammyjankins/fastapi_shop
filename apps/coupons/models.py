from typing import Optional

from bson import ObjectId
from fastapi import Form, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from pymongo import ASCENDING

from db import db

coupon_collection = db['coupon']
coupon_collection.create_index([("code", ASCENDING)], unique=True)


class CouponSchema(BaseModel):
    code: str
    valid_from: datetime = Field(default_factory=datetime.now)
    valid_to: datetime = Field(...)
    discount: int = Field(gt=0, lt=100, help_text='Percentage value (0 to 100)')
    active: bool


class CouponCreateSchema(BaseModel):
    code: str
    valid_from: Optional[datetime] = Field(None)
    valid_to: datetime
    discount: int = Field(gt=0, lt=100, help_text='Percentage value (0 to 100)')
    active: Optional[bool] = Field(False)

    @classmethod
    def as_form(
            cls,
            code: str = Form(...),
            valid_from: Optional[datetime] = Form(None),
            valid_to: datetime = Form(...),
            discount: int = Form(...),
            active: Optional[bool] = Form(False),
    ):
        return cls(
            code=code,
            valid_from=valid_from,
            valid_to=valid_to,
            discount=discount,
            active=active,

        )


def coupon_helper(coupon) -> dict:
    return {
        "_id": str(coupon["_id"]),
        "code": coupon["code"],
        "valid_from": coupon["valid_from"],
        "valid_to": coupon["valid_to"],
        "discount": coupon["discount"],
        "active": coupon["active"],

    }


async def create_coupon(coupon_data: dict):
    if coupon_data['valid_to'] <= coupon_data['valid_from']:
        raise HTTPException(status_code=422, detail="The coupon start date must be less than the expiration date!")

    coupon_data['active'] = True
    new_coupon = await coupon_collection.insert_one(coupon_data)
    created_coupon = await coupon_collection.find_one({"_id": new_coupon.inserted_id})
    return coupon_helper(created_coupon)


async def edit_coupon(_id: str, data: dict):
    if data['valid_to'] <= data['valid_from']:
        raise HTTPException(status_code=422, detail="The coupon start date must be less than the expiration date!")

    await coupon_collection.update_one({"_id": ObjectId(_id)}, {"$set": data})
    coupon = await get_coupon_by_id(_id)
    return coupon


async def get_coupon_by_code(code: str):
    coupon = await coupon_collection.find_one({"code": code})
    if coupon:
        return coupon_helper(coupon)


async def get_valid_coupon_by_code(code: str):
    coupon = await coupon_collection.find_one({"code": code,
                                               'active': True})
    if coupon:
        now = datetime.now()
        if not (coupon['valid_to'] > now > coupon['valid_from']):
            return None
    return coupon


async def get_valid_coupon_by_id(_id: str):
    coupon = await coupon_collection.find_one({"_id": ObjectId(_id),
                                               'active': True})
    if coupon:
        now = datetime.now()
        if not coupon['valid_to'] > now > coupon['valid_from']:
            return None
    return coupon


async def get_coupon_by_id(_id: str):
    coupon = await coupon_collection.find_one({"_id": ObjectId(_id)})
    if coupon:
        return coupon_helper(coupon)


async def get_all_coupons():
    coupons = []
    async for coupon in coupon_collection.find():
        coupons.append(coupon_helper(coupon))
    return coupons


async def get_valid_coupons():
    coupons = []
    now = datetime.now()

    async for coupon in coupon_collection.find({'active': True}):

        if coupon['valid_to'] > now > coupon['valid_from']:
            coupons.append(coupon_helper(coupon))
    return coupons
