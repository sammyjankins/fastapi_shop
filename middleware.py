import os

import jwt
from fastapi import Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware

from db import db

user_collection = db['user']

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


def get_user_from_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, os.environ.get('JWT_SECRET_KEY'), algorithms=[os.environ.get('ALGORITHM')])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


class AdminMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/admin"):
            token = request.cookies.get("token")
            user_subject = get_user_from_token(token)
            if not user_subject:
                return RedirectResponse(url='/user/login')
        response = await call_next(request)
        return response

