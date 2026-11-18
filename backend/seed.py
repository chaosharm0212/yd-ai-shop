"""演示数据：分类、商品、体验账号 demo / 123456。用法：cd backend && python seed.py"""
from decimal import Decimal

from app.db.database import Base, SessionLocal, engine
from app.models import Category, Product, User
from app.security import hash_password

CATEGORIES = [
    {"name": "手机数码", "sort": 1, "children": ["智能手机", "耳机音箱"]},
    {"name": "电脑办公", "sort": 2, "children": ["笔记本", "显示器"]},
    {"name": "家用电器", "sort": 3, "children": ["厨房电器"]},
]

PRODUCTS = [
    # (二级分类名, 名称, 现价, 原价, 库存, 销量, 描述)
    ("智能手机", "云东 X1 5G 手机 12+256G", 3299, 3699, 120, 356, "6.7 英寸直屏，5000mAh，支持 66W 快充。"),
    ("智能手机", "云东 Note 13 8+128G", 1299, 1499, 200, 812, "千元档长续航，5000 万像素主摄。"),
    ("耳机音箱", "云东 Buds Air 主动降噪耳机", 399, 499, 300, 1201, "42dB 主动降噪，单次续航 8 小时。"),
    ("耳机音箱", "云东 蓝牙音箱 Mini", 199, None, 80, 233, "IPX7 防水，户外便携。"),
    ("笔记本", "云东 Book Pro 14 锐龙版", 5499, 5999, 45, 96, "2.8K 120Hz 屏，1.4kg 轻薄本。"),
    ("显示器", "云东 27 英寸 2K 显示器", 1099, 1299, 60, 154, "IPS 面板，75Hz，支持 Type-C 65W 供电。"),
    ("厨房电器", "云东 破壁料理机", 499, 699, 70, 188, "1.75L 容量，12 档调速，可预约。"),
    ("厨房电器", "云东 电热水壶 1.7L", 129, 159, 150, 402, "304 不锈钢内胆，双层防烫。"),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == "demo").first() is None:
            db.add(
                User(
                    username="demo",
                    password_hash=hash_password("123456"),
                    nickname="体验用户",
                    phone="13800000000",
                    balance=Decimal("10000.00"),
                )
            )

        name_to_id: dict[str, int] = {}
        for group in CATEGORIES:
            top = db.query(Category).filter(Category.name == group["name"]).first()
            if top is None:
                top = Category(name=group["name"], sort=group["sort"], filter_attrs={"品牌": ["云东"]})
                db.add(top)
                db.flush()
            for child_name in group["children"]:
                child = db.query(Category).filter(Category.name == child_name).first()
                if child is None:
                    child = Category(name=child_name, parent_id=top.id, sort=0)
                    db.add(child)
                    db.flush()
                name_to_id[child_name] = child.id

        for idx, (cat, name, price, original, stock, sales, desc) in enumerate(PRODUCTS, start=1):
            if db.query(Product).filter(Product.name == name).first():
                continue
            db.add(
                Product(
                    category_id=name_to_id[cat],
                    name=name,
                    price=Decimal(price),
                    original_price=Decimal(original) if original else None,
                    stock=stock,
                    sales=sales,
                    main_image="/assets/placeholder.svg",
                    images=["/assets/placeholder.svg"],
                    description=desc,
                    specs=[
                        {"name": "颜色", "options": ["曜石黑", "云杉白"]},
                        {"name": "版本", "options": ["标准版", "尊享版"]},
                    ],
                    status=1,
                )
            )

        db.commit()
        print("seed 完成：体验账号 demo / 123456")
    finally:
        db.close()


if __name__ == "__main__":
    main()
