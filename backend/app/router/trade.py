"""交易：购物车、地址、订单（扣库存 + 扣余额 + 写流水）、钱包。"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Address, Cart, Order, OrderItem, Product, User, WalletLog
from app.router.deps import get_current_user
from app.schemas import (
    AddressCreate,
    AddressOut,
    CartAdd,
    CartItemOut,
    CartUpdate,
    OrderCreate,
    OrderItemOut,
    OrderOut,
    RechargeIn,
    WalletLogOut,
    WalletOut,
)
from app.services import gen_order_no

router = APIRouter(tags=["交易"])

D0 = Decimal("0.00")


def _money(v) -> Decimal:
    return Decimal(v).quantize(Decimal("0.01"))


def _order_out(order: Order, items: list[OrderItem]) -> OrderOut:
    return OrderOut(
        id=order.id,
        order_no=order.order_no,
        total_amount=_money(order.total_amount),
        status=order.status,
        payment_method=order.payment_method,
        paid_at=order.paid_at,
        created_at=order.created_at,
        items=[OrderItemOut.model_validate(i) for i in items],
    )


# ---------------- 购物车 ----------------
@router.post("/cart", response_model=CartItemOut, status_code=201, summary="加入购物车")
def add_to_cart(payload: CartAdd, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if product is None or product.status != 1:
        raise HTTPException(status_code=404, detail="商品不存在或已下架")

    row = db.scalar(
        select(Cart).where(
            Cart.user_id == user.id, Cart.product_id == product.id, Cart.sku == payload.sku
        )
    )
    if row:  # 同一商品同一规格累加，不新增行
        row.quantity += payload.quantity
    else:
        row = Cart(user_id=user.id, product_id=product.id, sku=payload.sku, quantity=payload.quantity)
        db.add(row)
    db.commit()
    db.refresh(row)
    return CartItemOut(
        id=row.id,
        product_id=product.id,
        name=product.name,
        price=_money(product.price),
        main_image=product.main_image,
        sku=row.sku,
        quantity=row.quantity,
        subtotal=_money(Decimal(product.price) * row.quantity),
    )


@router.get("/cart", response_model=list[CartItemOut], summary="购物车列表")
def list_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Cart, Product).join(Product, Product.id == Cart.product_id).where(Cart.user_id == user.id)
    ).all()
    return [
        CartItemOut(
            id=c.id,
            product_id=p.id,
            name=p.name,
            price=_money(p.price),
            main_image=p.main_image,
            sku=c.sku,
            quantity=c.quantity,
            subtotal=_money(Decimal(p.price) * c.quantity),
        )
        for c, p in rows
    ]


@router.patch("/cart/{cart_id}", response_model=list[CartItemOut], summary="改数量")
def update_cart(
    cart_id: int,
    payload: CartUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(Cart, cart_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="购物车记录不存在")
    row.quantity = payload.quantity
    db.commit()
    return list_cart(user, db)


@router.delete("/cart/{cart_id}", status_code=204, summary="删除购物车记录")
def delete_cart(cart_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Cart, cart_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="购物车记录不存在")
    db.delete(row)
    db.commit()


# ---------------- 地址 ----------------
@router.post("/addresses", response_model=AddressOut, status_code=201, summary="新增地址")
def create_address(
    payload: AddressCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if payload.is_default:
        # 默认地址最多一个：先把其它地址置 0（数据库没部分唯一索引，只能服务层保证）
        db.execute(update(Address).where(Address.user_id == user.id).values(is_default=False))
    addr = Address(user_id=user.id, **payload.model_dump())
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return addr


@router.get("/addresses", response_model=list[AddressOut], summary="地址列表")
def list_addresses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Address).where(Address.user_id == user.id).order_by(Address.id.desc())
    ).all()


# ---------------- 订单 ----------------
@router.post("/orders", response_model=OrderOut, status_code=201, summary="结算下单（扣库存 + 扣余额 + 写流水）")
def create_order(
    payload: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    addr = db.get(Address, payload.address_id)
    if addr is None or addr.user_id != user.id:
        raise HTTPException(status_code=400, detail="收货地址不存在")

    cart_rows = db.scalars(select(Cart).where(Cart.user_id == user.id)).all()
    if not cart_rows:
        raise HTTPException(status_code=400, detail="购物车是空的")

    # 先校验：任一商品下架/库存不足/超限就整单失败，不扣任何东西
    total = D0
    lines: list[tuple[Product, Cart]] = []
    for c in cart_rows:
        p = db.get(Product, c.product_id)
        if p is None or p.status != 1:
            raise HTTPException(status_code=400, detail="有商品已下架，请刷新购物车")
        if p.stock < c.quantity:
            raise HTTPException(status_code=400, detail=f"《{p.name}》库存不足")
        total += Decimal(p.price) * c.quantity
        lines.append((p, c))

    if payload.payment_method == "balance" and Decimal(user.balance) < total:
        raise HTTPException(status_code=400, detail="余额不足")

    order = Order(
        order_no=gen_order_no(),
        user_id=user.id,
        address_id=addr.id,
        total_amount=total,
        status="pending",
        payment_method=payload.payment_method,
    )
    db.add(order)
    db.flush()  # 拿到 order.id

    items: list[OrderItem] = []
    for p, c in lines:
        p.stock -= c.quantity
        p.sales += c.quantity
        item = OrderItem(
            order_id=order.id,
            product_id=p.id,
            name=p.name,  # 快照
            price=p.price,  # 快照：成交单价
            quantity=c.quantity,
            sku=c.sku,
            image=p.main_image,
        )
        db.add(item)
        items.append(item)

    if payload.payment_method == "balance":
        user.balance = Decimal(user.balance) - total
        order.status = "paid"
        order.paid_at = datetime.now()
        db.add(
            WalletLog(
                user_id=user.id,
                type="pay",
                amount=-total,
                balance_after=_money(user.balance),
                remark=f"订单{order.order_no}",
            )
        )

    for c in cart_rows:  # 下单后清空购物车
        db.delete(c)

    db.commit()
    db.refresh(order)
    for i in items:
        db.refresh(i)
    return _order_out(order, items)


@router.get("/orders", response_model=list[OrderOut], summary="我的订单")
def list_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.scalars(
        select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())
    ).all()
    result = []
    for o in orders:
        items = db.scalars(select(OrderItem).where(OrderItem.order_id == o.id)).all()
        result.append(_order_out(o, items))
    return result


@router.post("/orders/{order_id}/cancel", response_model=OrderOut, summary="取消订单（退余额 + 回滚库存）")
def cancel_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ("pending", "paid"):
        raise HTTPException(status_code=400, detail=f"当前状态 {order.status} 不可取消")

    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    for i in items:
        p = db.get(Product, i.product_id)
        if p:
            p.stock += i.quantity
            p.sales = max(0, p.sales - i.quantity)

    if order.status == "paid":
        amount = _money(order.total_amount)
        user.balance = Decimal(user.balance) + amount
        db.add(
            WalletLog(
                user_id=user.id,
                type="refund",
                amount=amount,
                balance_after=_money(user.balance),
                remark=f"取消订单{order.order_no}",
            )
        )
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    return _order_out(order, items)


# ---------------- 钱包 ----------------
@router.get("/wallet", response_model=WalletOut, summary="查询余额")
def get_wallet(user: User = Depends(get_current_user)):
    return WalletOut(balance=_money(user.balance))


@router.post("/wallet/recharge", response_model=WalletOut, summary="充值")
def recharge(payload: RechargeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    amount = _money(payload.amount)
    user.balance = Decimal(user.balance) + amount
    db.add(
        WalletLog(
            user_id=user.id,
            type="recharge",
            amount=amount,
            balance_after=_money(user.balance),
            remark="在线充值",
        )
    )
    db.commit()
    return WalletOut(balance=_money(user.balance))


@router.get("/wallet/logs", response_model=list[WalletLogOut], summary="钱包流水")
def wallet_logs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(WalletLog).where(WalletLog.user_id == user.id).order_by(WalletLog.id.desc()).limit(50)
    ).all()
