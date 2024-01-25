import os

import stripe
from bson import ObjectId
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from stripe.error import SignatureVerificationError

from apps.order.models import get_order_by_id, OrderSchema
from apps.product.models import get_product_by_id
from celery_tasks import send_bill_email
from db import db
from dependencies import templates
from recommender import Recommender
from utils import Message, get_stripe_url

order_collection = db['order']

router = APIRouter()

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
stripe.api_version = '2022-11-15'


@router.get('/process')
async def payment_process_get(request: Request):
    order_id = request.cookies.get('order_id')
    order = OrderSchema(**await get_order_by_id(order_id))
    products = {item.product_id: await get_product_by_id(item.product_id) for item in order.items}
    return templates.TemplateResponse("shop/payment/process.html", {"request": request, "order": order,
                                                                    "products": products})


@router.post('/process')
async def payment_process_post(request: Request):
    order_id = request.cookies.get('order_id')
    order = OrderSchema(**await get_order_by_id(order_id))
    success_url = request.url._url.replace('process', 'completed')
    cancel_url = request.url._url.replace('process', 'canceled')

    session_data = {
        'mode': 'payment',
        'client_reference_id': order_id,
        'success_url': success_url,
        'cancel_url': cancel_url,
        'line_items': []
    }

    for item in order.items:
        session_data['line_items'].append({
            'price_data': {
                'unit_amount': int(item.price * float('100')),
                'currency': 'cad',
                'product_data': {
                    'name': item.product_name,
                },
            },
            'quantity': item.quantity,
        })

    if order.coupon:
        stripe_coupon = stripe.Coupon.create(
            name=order.coupon["code"],
            percent_off=order.discount,
            duration='once',
        )
        session_data['discounts'] = [{
            'coupon': stripe_coupon.id
        }]

    session = stripe.checkout.Session.create(**session_data)

    return RedirectResponse(url=session.url, status_code=303)


@router.get('/completed')
async def payment_completed(request: Request):
    order_id = request.cookies.get('order_id')
    order = OrderSchema(**await get_order_by_id(order_id))
    return templates.TemplateResponse("shop/payment/completed.html", {"request": request, "order": order})


@router.get('/canceled')
async def payment_canceled(request: Request):
    return templates.TemplateResponse("shop/payment/canceled.html", {"request": request})


@router.post('/webhook/')
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers['stripe-signature']
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            os.environ.get('STRIPE_WEBHOOK_SECRET'))
    except ValueError as e:
        print(e)
        return templates.TemplateResponse("shop/payment/completed.html",
                                          {"request": request,
                                           'messages': [Message('Invalid payload received by webhook')]})
    except SignatureVerificationError as e:
        print(e)
        return templates.TemplateResponse("shop/payment/completed.html",
                                          {"request": request,
                                           'messages': [Message('Invalid signature')]})

    if event.type == 'checkout.session.completed':
        session = event.data.object
        if session.mode == 'payment' and session.payment_status == 'paid':
            order_data = await get_order_by_id(session.client_reference_id)
            if not order_data:
                return Response(status_code=404)

            stripe_id = session.payment_intent
            stripe_url = get_stripe_url(stripe_id)

            order_data['paid'] = True
            order_data['stripe_id'] = stripe_id
            order_data['stripe_url'] = stripe_url
            await order_collection.replace_one({'_id': order_data['_id']}, order_data)
            order = convert_object_id_to_str(await get_order_by_id(order_data['_id']))
            ids = [item["product_id"] for item in order['items']]
            r = Recommender(ids)
            r.products_bought()
            send_bill_email.delay(order)


def convert_object_id_to_str(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = convert_object_id_to_str(value)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            obj[i] = convert_object_id_to_str(item)
    elif isinstance(obj, ObjectId):
        obj = str(obj)
    return obj
