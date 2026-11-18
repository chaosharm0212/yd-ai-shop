"""商品与分类：列表（分页/搜索/筛选/排序）、详情、分类树。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Category, Product
from app.schemas import CategoryOut, CategoryTreeOut, ProductOut, ProductPageOut

router = APIRouter(tags=["商品"])

_SORT = {
    "default": Product.id.desc(),
    "sales": Product.sales.desc(),
    "price_asc": Product.price.asc(),
    "price_desc": Product.price.desc(),
}


@router.get("/categories", response_model=list[CategoryTreeOut], summary="分类树（一级 + 二级）")
def category_tree(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Category).where(Category.is_enabled.is_(True)).order_by(Category.sort, Category.id)
    ).all()
    tops = {c.id: CategoryTreeOut(**CategoryOut.model_validate(c).model_dump()) for c in rows if not c.parent_id}
    for c in rows:
        if c.parent_id and c.parent_id in tops:
            tops[c.parent_id].children.append(CategoryOut.model_validate(c))
    return sorted(tops.values(), key=lambda x: x.sort)


@router.get("/products", response_model=ProductPageOut, summary="商品列表")
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=50),
    keyword: str | None = Query(None, max_length=50),
    category_id: int | None = None,
    sort: str = Query("default", pattern="^(default|sales|price_asc|price_desc)$"),
    db: Session = Depends(get_db),
):
    stmt = select(Product).where(Product.status == 1)
    if keyword:
        stmt = stmt.where(Product.name.like(f"%{keyword}%"))
    if category_id:
        child_ids = db.scalars(select(Category.id).where(Category.parent_id == category_id)).all()
        stmt = stmt.where(Product.category_id.in_([category_id, *child_ids]))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(_SORT[sort]).offset((page - 1) * size).limit(size)).all()
    return ProductPageOut(
        items=[ProductOut.model_validate(p) for p in items], total=total, page=page, size=size
    )


@router.get("/products/{product_id}", response_model=ProductOut, summary="商品详情")
def product_detail(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or product.status != 1:
        raise HTTPException(status_code=404, detail="商品不存在或已下架")
    return product
