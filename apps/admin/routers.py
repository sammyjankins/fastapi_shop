from bson.errors import InvalidId
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from pymongo.errors import DuplicateKeyError

import apps.category.models as cat_m
import apps.coupons.models as coup_m
import apps.order.models as ord_m
import apps.product.models as prod_m
from db import delete_objects, delete_object
from dependencies import templates
from utils import Paginator, Message

router = APIRouter()


@router.get("/", response_model=dict)
async def get_admin(request: Request):
    return templates.TemplateResponse("admin/home.html", {"request": request, 'admin': True})


# CATEGORY ADMIN CRUD ROUTING

# TODO поменять использование category.id на category._id  в моделях и шаблонах
@router.get("/category/", response_model=dict)
async def admin_category_list_endpoint(request: Request,
                                       pagination: Paginator = Depends(Paginator(cat_m.get_all_categories))):
    categories = await cat_m.get_all_categories()
    context = {"request": request, "categories": categories[pagination.start:pagination.end],
               'admin': True,
               "paginator": pagination}

    return await list_endpoint_dry(request, context, model='category')


@router.get("/category/create", response_model=dict)
async def admin_category_create_endpoint(request: Request):
    context = {"request": request, 'admin': True}

    if request.cookies.get('category_created') == 'True':
        context.update({'messages': [Message(text=f'New category has been created', tags='info')]})
        response = templates.TemplateResponse("admin/category/create.html", context=context)
        response.set_cookie('category_created', 'False')
    else:
        response = templates.TemplateResponse("admin/category/create.html", context=context)
    return response


@router.post("/category/create", response_model=dict)
async def admin_category_create_endpoint(request: Request,
                                         next_page: str = Form(...),
                                         form: cat_m.CategoryCreateSchema = Depends(
                                             cat_m.CategoryCreateSchema.as_form), ):
    try:
        category = await cat_m.create_category(form.model_dump())
        redirect_url = next_page if next_page == 'create' else f'edit/{category["_id"]}'

        response = RedirectResponse(url=redirect_url,
                                    status_code=303, )
        response.set_cookie('category_created', 'True')
    except DuplicateKeyError as e:
        messages = [Message(f"A category called {form.model_dump()['name']} already exists! "
                            f"Please type a different name for the category.")]
        response = templates.TemplateResponse("admin/category/create.html",
                                              {"request": request, 'admin': True, "messages": messages, "form": form})
    return response


@router.get("/category/edit/{_id}", response_model=dict)
async def admin_category_edit_endpoint(request: Request, _id: str):
    category = await cat_m.get_category_by_id(_id)
    context = {"request": request, "category": category, 'admin': True}
    if request.cookies.get('category_created') == 'True':
        context.update({'messages': [Message(text=f'New category {category["name"]} has been created', tags='info')]})
        response = templates.TemplateResponse("admin/category/edit.html", context=context)
        response.set_cookie('category_created', 'False')
    else:
        response = templates.TemplateResponse("admin/category/edit.html", context=context)
    return response


@router.post("/category/edit/{_id}", response_model=dict)
async def admin_category_edit_endpoint(request: Request,
                                       _id: str,
                                       form: cat_m.CategoryCreateSchema = Depends(
                                           cat_m.CategoryCreateSchema.as_form), ):
    edited_category = await cat_m.edit_category(_id, form.model_dump())
    message = [Message(text=f'Product {edited_category["name"]} has been edited', tags='info')]

    return templates.TemplateResponse("admin/category/edit.html",
                                      {"request": request,
                                       "category": edited_category,
                                       "messages": message,
                                       'admin': True})


@router.get("/category/delete/{_id}", response_model=dict)
async def admin_category_delete_endpoint(request: Request, _id: str):
    category = await cat_m.get_category_by_id(_id)
    return templates.TemplateResponse("admin/category/delete_confirm.html",
                                      {"request": request, "category": category, 'admin': True})


@router.get("/category/delete_confirm/{_id}", response_model=dict)
async def admin_category_delete_confirm_endpoint(request: Request, _id: str):
    await delete_object(_id, 'category')
    response = RedirectResponse(url='/admin/category/',
                                status_code=303, )
    response.set_cookie('category_deleted', 'True')
    return response


# PRODUCT ADMIN CRUD ROUTING


@router.get("/product/", response_model=dict)
async def admin_product_list_endpoint(request: Request,
                                      pagination: Paginator = Depends(Paginator(prod_m.get_all_products))):
    products = await prod_m.get_all_products()
    context = {"request": request, "products": products[pagination.start:pagination.end],
               'admin': True,
               'paginator': pagination}

    return await list_endpoint_dry(request, context, model='product')


@router.get("/product/create", response_model=dict)
async def admin_product_create_endpoint(request: Request, categories_list: list = Depends(cat_m.get_all_categories)):
    context = {"request": request, "categories_list": categories_list, 'admin': True}
    if request.cookies.get('product_created') == 'True':
        context.update({'messages': [Message(text=f'New product has been created', tags='info')]})
        response = templates.TemplateResponse("admin/product/create.html", context=context)
        response.set_cookie('product_created', 'False')
    else:
        response = templates.TemplateResponse("admin/product/create.html", context=context)
    return response


@router.post("/product/create", response_model=dict)
async def admin_product_create_endpoint(request: Request,
                                        next_page: str = Form(...),
                                        form: prod_m.ProductCreateSchema = Depends(
                                            prod_m.ProductCreateSchema.as_form), ):
    try:
        product = await prod_m.create_product(form.model_dump())

        redirect_url = next_page if next_page == 'create' else f'edit/{product["_id"]}'
        response = RedirectResponse(url=redirect_url,
                                    status_code=303, )
        response.set_cookie('product_created', 'True')
        return response
    except Exception as e:
        if isinstance(e, InvalidId):
            messages = [Message('You must select a category')]
        else:
            messages = [Message(e.detail)]
        categories_list = await cat_m.get_all_categories()
        return templates.TemplateResponse("admin/product/create.html",
                                          {"request": request, "categories_list": categories_list, 'admin': True,
                                           "messages": messages})


@router.get("/product/edit/{_id}", response_model=dict)
async def admin_product_edit_endpoint(request: Request, _id: str,
                                      categories_list: list = Depends(cat_m.get_all_categories)):
    product = await prod_m.get_product_by_id(_id)

    context = {"request": request, "product": product, "categories_list": categories_list, 'admin': True}

    if request.cookies.get('product_created') == 'True':
        context.update({'messages': [Message(text=f'New product {product["name"]} has been created', tags='info')]})
        response = templates.TemplateResponse("admin/product/edit.html", context=context)
        response.set_cookie('product_created', 'False')
    else:
        response = templates.TemplateResponse("admin/product/edit.html", context=context)
    return response


@router.post("/product/edit/{_id}", response_model=dict)
async def admin_product_edit_endpoint(request: Request,
                                      _id: str,
                                      form: prod_m.ProductCreateSchema = Depends(prod_m.ProductCreateSchema.as_form),
                                      categories_list: list = Depends(cat_m.get_all_categories)):
    edited_product = await prod_m.edit_product(_id, form.model_dump())
    message = [Message(text=f'Product {edited_product["name"]} has been edited', tags='info')]

    return templates.TemplateResponse("admin/product/edit.html",
                                      {"request": request, "product": edited_product,
                                       "categories_list": categories_list,
                                       'messages': message,
                                       'admin': True})


@router.get("/product/delete/{_id}", response_model=dict)
async def admin_product_delete_endpoint(request: Request, _id: str):
    product = await prod_m.get_product_by_id(_id)
    return templates.TemplateResponse("admin/product/delete_confirm.html",
                                      {"request": request, "product": product, 'admin': True})


@router.get("/product/delete_confirm/{_id}", response_model=dict)
async def admin_product_delete_confirm_endpoint(request: Request, _id: str):
    await delete_object(_id, 'product')
    response = RedirectResponse(url='/admin/product/',
                                status_code=303, )
    response.set_cookie('product_deleted', 'True')
    return response


# ORDER ADMIN CRUD ROUTING

@router.get("/order/", response_model=dict)
async def admin_order_list_endpoint(request: Request,
                                    pagination: Paginator = Depends(Paginator(ord_m.get_all_orders))):
    orders = await ord_m.get_all_orders()
    context = {"request": request, "orders": orders[pagination.start:pagination.end],
               'admin': True,
               'paginator': pagination}

    return await list_endpoint_dry(request, context, model='order')


@router.get("/order/create", response_model=dict)
async def admin_order_create_endpoint(request: Request, coupons_list: list = Depends(coup_m.get_valid_coupons)):
    context = {"request": request, "coupons_list": coupons_list, 'admin': True}

    if request.cookies.get('order_created') == 'True':
        context.update({'messages': [Message(text=f'New order has been created', tags='info')]})
        response = templates.TemplateResponse("admin/order/create.html", context=context)
        response.set_cookie('order_created', 'False')
    else:
        response = templates.TemplateResponse("admin/order/create.html", context=context)
    return response


@router.post("/order/create", response_model=dict)
async def admin_order_create_endpoint(request: Request,
                                      next_page: str = Form(...),
                                      form: ord_m.OrderCreateSchema = Depends(ord_m.OrderCreateSchema.as_form),
                                      coupons_list: list = Depends(coup_m.get_valid_coupons)):
    coupon = await coup_m.get_coupon_by_id(form.coupon)
    try:
        order_data = form.model_dump()
        items_data = [{"product_id": product, "quantity": quantity}
                      for product, quantity
                      in zip(order_data['products'], order_data['quantities'])]
        order = await ord_m.create_order(order_data=order_data, items=items_data)

        redirect_url = next_page if next_page == 'create' else f'edit/{order["_id"]}'
        response = RedirectResponse(url=redirect_url,
                                    status_code=303, )
        response.set_cookie('order_created', 'True')
    except Exception as e:
        messages = [Message(e.detail)]
        response = templates.TemplateResponse("admin/order/create.html",
                                              {"request": request, "coupons_list": coupons_list,
                                               'admin': True, "messages": messages,
                                               "form": form, "coupon": coupon})
    return response


@router.get("/order/edit/{_id}", response_model=dict)
async def admin_order_edit_endpoint(request: Request, _id: str, coupons_list: list = Depends(coup_m.get_valid_coupons)):
    order = await ord_m.get_order_by_id(_id)
    coupon = await coup_m.get_coupon_by_id(order["coupon"]['_id']) if order.get("coupon") else None
    items = await ord_m.get_order_items(order["items"])

    context = {"request": request, "order": order, "coupons_list": coupons_list,
               "coupon": coupon,
               'admin': True, "items": items, 'messages': []}

    if request.cookies.get('order_created') == 'True':
        context['messages'].append(Message(text=f'New order {order["_id"]} has been created', tags='info'))
        response = templates.TemplateResponse("admin/order/edit.html", context=context)
        response.set_cookie('order_created', 'False')
    else:
        if (message := request.cookies.get('error_msg')) != 'False':
            context['messages'].append(Message(text=message))
        response = templates.TemplateResponse("admin/order/edit.html", context=context)
        if request.cookies.get('error_msg') != 'False':
            response.set_cookie('error_msg', 'False')
    return response


@router.post("/order/edit/{_id}", response_model=dict)
async def admin_order_edit_endpoint(request: Request,
                                    _id: str,
                                    form: ord_m.OrderCreateSchema = Depends(ord_m.OrderCreateSchema.as_form),
                                    coupons_list: list = Depends(coup_m.get_valid_coupons)):
    try:
        order = await ord_m.edit_order(_id, form.model_dump())
        coupon = order.get('coupon')
        message = [Message(text=f'Order {order["_id"]} has been edited', tags='info')]
    except HTTPException as e:
        order = await ord_m.get_order_by_id(_id)
        coupon = await coup_m.get_coupon_by_id(order["coupon"]['_id']) if order.get("coupon") else None
        message = [Message(text=e.detail, tags='danger')]

    context = {"request": request, "order": order, "coupon": coupon,
               "coupons_list": coupons_list,
               'messages': message,
               'admin': True}

    items = await ord_m.get_order_items(order["items"])
    context.update({"items": items})

    return templates.TemplateResponse("admin/order/edit.html", context)


@router.get("/order/delete/{_id}", response_model=dict)
async def admin_order_delete_endpoint(request: Request, _id: str):
    return templates.TemplateResponse("admin/order/delete_confirm.html",
                                      {"request": request, "order_id": _id, 'admin': True})


@router.get("/order/delete_confirm/{_id}", response_model=dict)
async def admin_order_delete_confirm_endpoint(request: Request, _id: str):
    await delete_object(_id, 'order')
    response = RedirectResponse(url='/admin/order/',
                                status_code=303, )
    response.set_cookie('order_deleted', 'True')
    return response


# COUPON ADMIN CRUD ROUTING
@router.get("/coupon/", response_model=dict)
async def admin_coupon_list_endpoint(request: Request,
                                     pagination: Paginator = Depends(Paginator(coup_m.get_all_coupons))):
    coupons = await coup_m.get_all_coupons()
    context = {"request": request, "coupons": coupons[pagination.start:pagination.end],
               'admin': True,
               'paginator': pagination}

    return await list_endpoint_dry(request, context, model='coupon')


@router.get("/coupon/create", response_model=dict)
async def admin_coupon_create_endpoint(request: Request):
    context = {"request": request, 'admin': True}

    if request.cookies.get('coupon_created') == 'True':
        context.update({'messages': [Message(text=f'New coupon has been created', tags='info')]})
        response = templates.TemplateResponse("admin/coupon/create.html", context=context)
        response.set_cookie('coupon_created', 'False')
    else:
        response = templates.TemplateResponse("admin/coupon/create.html", context=context)
    return response


@router.post("/coupon/create", response_model=dict)
async def admin_coupon_create_endpoint(request: Request,
                                       next_page: str = Form(...),
                                       form: coup_m.CouponCreateSchema = Depends(coup_m.CouponCreateSchema.as_form)):
    try:
        coupon_data = form.model_dump()
        coupon = await coup_m.create_coupon(coupon_data)

        redirect_url = next_page if next_page == 'create' else f'edit/{coupon["_id"]}'
        response = RedirectResponse(url=redirect_url,
                                    status_code=303, )
        response.set_cookie('coupon_created', 'True')
    except Exception as e:
        messages = [Message(e.detail)]
        response = templates.TemplateResponse("admin/coupon/create.html",
                                              {"request": request, 'admin': True, "messages": messages, "form": form})
    return response


@router.get("/coupon/edit/{_id}", response_model=dict)
async def admin_coupon_edit_endpoint(request: Request, _id: str):
    coupon = await coup_m.get_coupon_by_id(_id)
    context = {"request": request, "coupon": coupon, 'admin': True, }

    if request.cookies.get('coupon_created') == 'True':
        context.update({'messages': [Message(text=f'New coupon {coupon["_id"]} has been created', tags='info')]})
        response = templates.TemplateResponse("admin/coupon/edit.html", context=context)
        response.set_cookie('coupon_created', 'False')
    else:
        response = templates.TemplateResponse("admin/coupon/edit.html", context=context)
    return response


@router.post("/coupon/edit/{_id}", response_model=dict)
async def admin_coupon_edit_endpoint(request: Request,
                                     _id: str,
                                     form: coup_m.CouponCreateSchema = Depends(coup_m.CouponCreateSchema.as_form)):
    try:
        coupon = await coup_m.edit_coupon(_id, form.model_dump())
        message = [Message(text=f'Coupon {coupon["_id"]} has been edited', tags='info')]
    except HTTPException as e:
        coupon = await coup_m.get_coupon_by_id(_id)
        message = [Message(text=e.detail, tags='danger')]

    context = {"request": request, "coupon": coupon, 'messages': message, 'admin': True}

    return templates.TemplateResponse("admin/coupon/edit.html", context)


@router.get("/coupon/delete/{_id}", response_model=dict)
async def admin_coupon_delete_endpoint(request: Request, _id: str):
    coupon = await coup_m.get_coupon_by_id(_id)
    return templates.TemplateResponse("admin/coupon/delete_confirm.html",
                                      {"request": request, "coupon": coupon, 'admin': True})


@router.get("/coupon/delete_confirm/{_id}", response_model=dict)
async def admin_coupon_delete_confirm_endpoint(request: Request, _id: str):
    await delete_object(_id, 'coupon')
    response = RedirectResponse(url='/admin/coupon/',
                                status_code=303, )
    response.set_cookie('coupon_deleted', 'True')
    return response


# GENERAL


@router.post("/objects/delete/{model}", response_model=dict, name="admin_objects_delete_endpoint")
async def admin_objects_delete_endpoint(request: Request, model: str, delete: list[str] = Form(...)):
    if delete[0] == 'on':
        delete = delete[1:]
    return templates.TemplateResponse("admin/objects/delete_confirm.html",
                                      {"request": request, "model": model, "delete": delete, 'admin': True})


@router.post("/objects/delete_confirm/{model}", response_model=dict)
async def admin_objects_delete_confirm_endpoint(request: Request, model: str, delete: str = Form(...)):
    await delete_objects(delete, model)
    response = RedirectResponse(url=f'/admin/{model}/',
                                status_code=303, )
    response.set_cookie('objects_deleted', 'True')
    return response


async def list_endpoint_dry(request: Request, context: dict, model: str):
    """
    Common operation for listing endpoints.

    :param request: Request object from the FastAPI application.
    :param context: Dictionary containing data to be passed to the template.
    :param model: String representing the model for which the listing endpoint is called.
    :return: TemplateResponse for rendering the list.
    """
    message = None
    cookie_to_unset = None

    if request.cookies.get(f'{model}_deleted') == 'True':
        message = f'{model.capitalize()} has been deleted'
        cookie_to_unset = f'{model}_deleted'
    elif request.cookies.get('objects_deleted') == 'True':
        message = f'{model.capitalize()} objects has been deleted'
        cookie_to_unset = 'objects_deleted'

    if message:
        context.update({'messages': [Message(text=message, tags='info')]})

    response = templates.TemplateResponse(f'admin/{model}/list.html', context=context)

    if cookie_to_unset:
        response.set_cookie(cookie_to_unset, 'False')
    return response
