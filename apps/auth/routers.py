import os
from typing import Annotated

import jwt
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from apps.auth.models import User
from apps.cart.cart import CartManager
from apps.cart.routers import get_current_cart
from db import db
from dependencies import templates
from utils import Message

router = APIRouter()

user_collection = db['user']

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


def create_jwt(data: dict):
    return jwt.encode(data, os.environ.get('JWT_SECRET_KEY'), algorithm=os.environ.get('ALGORITHM'))


async def get_user(username: str):
    user = await user_collection.find_one({"username": username})
    if user:
        return User(**user)


@router.get("/login")
async def login(request: Request, current_cart: CartManager = Depends(get_current_cart)):
    return templates.TemplateResponse("user/auth/login.html", {"request": request, "cart": current_cart})


@router.post("/login")
async def login(request: Request, user_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                current_cart: CartManager = Depends(get_current_cart)):
    user_data_from_db = await get_user(user_data.username)
    if user_data_from_db is None or user_data.password != user_data_from_db.password:
        return templates.TemplateResponse("user/auth/login.html", {"request": request, "cart": current_cart,
                                                                   "messages": [Message('Invalid credentials')]})

        # raise HTTPException(
        #     status_code=status.HTTP_401_UNAUTHORIZED,
        #     detail="Invalid credentials",
        #     headers={'WWW-Authenticate': 'Bearer'}
        # )
    token = create_jwt({'sub': user_data.username})
    response = RedirectResponse(url='/admin', status_code=303)
    response.set_cookie('token', token)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/product", status_code=303)
    response.delete_cookie('token')
    return response
