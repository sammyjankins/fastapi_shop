from bson import ObjectId
from fastapi import APIRouter, Request, HTTPException, Depends

from apps.cart.cart import CartManager
from apps.cart.routers import get_current_cart
from apps.category.models import get_all_categories, get_category_by_slug, get_category_by_id
from apps.product.models import ProductSchema, create_product, get_products_by_category, get_all_products, \
    get_product_by_slug, ProductCreateSchema, get_available_products
from dependencies import templates
from recommender import Recommender
from utils import Message

router = APIRouter()


@router.post("/")
async def create_product_endpoint(product: ProductCreateSchema = Depends(ProductCreateSchema)):
    return await create_product(product_data=product.model_dump())


@router.get("/", response_model=dict)
async def product_list_endpoint(request: Request, current_cart: CartManager = Depends(get_current_cart)):
    categories = await get_all_categories()
    products = await get_available_products()

    return templates.TemplateResponse("shop/product/list.html", {"request": request, "categories": categories,
                                                                 "products": products, "cart": current_cart})


@router.get("/{category_slug}", response_model=dict)
async def product_list_by_category_endpoint(request: Request, category_slug: str,
                                            current_cart: CartManager = Depends(get_current_cart)):
    categories = await get_all_categories()
    category = await get_category_by_slug(slug=category_slug)
    products = await get_products_by_category(category=category)

    return templates.TemplateResponse("shop/product/list.html", {"request": request, "category": category,
                                                                 "categories": categories, "products": products,
                                                                 "cart": current_cart})


@router.get("/{_id}/{slug}", response_model=ProductSchema)
async def product_detail(request: Request, _id: str, slug: str, current_cart: CartManager = Depends(get_current_cart)):
    product_schema = await get_product_by_slug(_id=ObjectId(_id), slug=slug)
    category = await get_category_by_id(_id=product_schema['category_id'])
    context = {"request": request, "product": product_schema,
               "category": category, "cart": current_cart}
    if product_schema:
        r = Recommender([product_schema['_id']])
        recommendations = await r.suggest_products_for()
        context.update({'recommendations': recommendations})

        if request.cookies.get('cart_updated') == '1':
            context.update({'messages': [Message(text='Product has been added to cart', tags='info')]})
            response = templates.TemplateResponse("shop/product/detail.html", context=context)
            response.set_cookie('cart_updated', '0')
        else:
            response = templates.TemplateResponse("shop/product/detail.html", context=context)
        return response

    raise HTTPException(status_code=404, detail="Category not found")
