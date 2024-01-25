from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse

from apps.cart.cart import CartManager
from db import db
from dependencies import templates, get_current_cart
from recommender import Recommender

router = APIRouter()

cart_collection = db['cart']


@router.post("/add")
async def add_to_cart(request: Request,
                      product_id: str = Form(...),
                      quantity: int = Form(gt=0),
                      override_quantity: bool = Form(False),
                      current_cart: CartManager = Depends(get_current_cart)):
    await current_cart.add(product_id, override_quantity, quantity)
    redir_resp = RedirectResponse(url=request.headers['referer'].removeprefix(f'{request.headers["origin"]}'),
                                  status_code=303)
    redir_resp.set_cookie('cart_updated', '1')
    await current_cart.save(redir_resp)
    return redir_resp


@router.post("/remove")
async def remove_from_cart(product_id: str = Form(...), current_cart: CartManager = Depends(get_current_cart)):
    redir_resp = RedirectResponse(url='/cart', status_code=303)
    await current_cart.remove(product_id, redir_resp)
    return redir_resp


@router.get('/')
async def cart_detail(request: Request, current_cart: CartManager = Depends(get_current_cart)):
    await current_cart.set_coupon()
    if len(current_cart):

        items = [item async for item in current_cart]
        r = Recommender([str(item['product']['_id']) for item in items])
        recommendations = await r.suggest_products_for()
        response = templates.TemplateResponse("shop/cart/detail.html", {"request": request, "cart": current_cart,
                                                                        "items": items,
                                                                        'recommendations': recommendations})
        return response
    else:
        return RedirectResponse(url='/product', status_code=303)
