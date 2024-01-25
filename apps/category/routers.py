from fastapi import APIRouter, Body, HTTPException

from apps.category.models import CategorySchema, create_category, get_all_categories, get_category_by_slug, \
    get_category_by_id

router = APIRouter()


@router.post("/")
async def create_category_endpoint(category: CategorySchema = Body(default=None)):
    category_data = await create_category(category.model_dump())
    return category_data


@router.get("/")
async def get_all_categories_endpoint():
    categories = await get_all_categories()
    return categories


@router.get("/{slug}", response_model=CategorySchema)
async def get_category_by_slug_endpoint(slug: str):
    category_schema = await get_category_by_slug(slug=slug)
    if category_schema:
        return category_schema
    raise HTTPException(status_code=404, detail="Category not found")


@router.get("/{_id}", response_model=CategorySchema)
async def get_category_by_id_endpoint(_id: str):
    category_schema = await get_category_by_id(_id=_id)
    if category_schema:
        return category_schema
    raise HTTPException(status_code=404, detail="Category not found")
