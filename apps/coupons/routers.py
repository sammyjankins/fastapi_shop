from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from apps.coupons.models import get_valid_coupon_by_code

router = APIRouter()


@router.post("/apply")
async def coupon_apply(request: Request, coupon_code: str = Form(...)):
    response = RedirectResponse(url='/cart', status_code=303)
    if coupon_code:
        coupon = await get_valid_coupon_by_code(code=coupon_code)
        if coupon:
            response.set_cookie('coupon_id', str(coupon["_id"]))

    return response
