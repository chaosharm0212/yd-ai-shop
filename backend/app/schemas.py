"""Pydantic 契约：请求/响应模型，既是校验器又是 /docs 里的接口文档。"""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------- 用户 ----------------
class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=64)
    phone: str | None = Field(default=None, max_length=20)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: int
    username: str
    nickname: str
    phone: str | None
    balance: Decimal
    is_enabled: bool


# ---------------- 分类 / 商品 ----------------
class CategoryOut(ORMModel):
    id: int
    name: str
    parent_id: int | None
    sort: int
    filter_attrs: dict | None = None


class CategoryTreeOut(CategoryOut):
    children: list["CategoryOut"] = []


class ProductOut(ORMModel):
    id: int
    category_id: int
    name: str
    price: Decimal
    original_price: Decimal | None
    stock: int
    sales: int
    main_image: str | None
    images: list | None = None
    description: str | None = None
    specs: list | None = None
    status: int


class ProductPageOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    size: int


# ---------------- 购物车 ----------------
class CartAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)
    sku: str | None = Field(default=None, max_length=64)


class CartUpdate(BaseModel):
    quantity: int = Field(ge=1, le=99)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    name: str
    price: Decimal
    main_image: str | None
    sku: str | None
    quantity: int
    subtotal: Decimal


# ---------------- 地址 ----------------
class AddressCreate(BaseModel):
    receiver: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=5, max_length=20)
    province: str = Field(max_length=50)
    city: str = Field(max_length=50)
    district: str = Field(max_length=50)
    detail: str = Field(min_length=1, max_length=200)
    is_default: bool = False


class AddressOut(ORMModel):
    id: int
    receiver: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    is_default: bool


# ---------------- 订单 / 钱包 ----------------
class OrderCreate(BaseModel):
    address_id: int
    payment_method: Literal["balance", "alipay"] = "balance"


class OrderItemOut(ORMModel):
    product_id: int
    name: str
    price: Decimal
    quantity: int
    sku: str | None
    image: str | None


class OrderOut(ORMModel):
    id: int
    order_no: str
    total_amount: Decimal
    status: str
    payment_method: str | None
    paid_at: datetime | None
    created_at: datetime
    items: list[OrderItemOut] = []


class RechargeIn(BaseModel):
    amount: Decimal = Field(gt=0, le=Decimal("10000"), decimal_places=2)


class WalletOut(BaseModel):
    balance: Decimal


class WalletLogOut(ORMModel):
    id: int
    type: str
    amount: Decimal
    balance_after: Decimal
    remark: str | None
    created_at: datetime
