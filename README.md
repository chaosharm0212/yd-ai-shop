# 云东AI购 · 自营 B2C 商城（Day1 骨架）

前后端分离的电商项目骨架：FastAPI + SQLAlchemy + MySQL 8 + 静态前端（Vue/原生 JS 均可，本仓库用原生 JS 免构建）。

## 目录结构

```
yd-ai-shop/
├── requirements.txt        # 依赖清单
├── .env.example            # 配置模板（可提交）
├── database/init.sql       # 建库建表 DDL（16 张表）
├── backend/
│   ├── main.py             # 应用入口（/health、/docs、静态资源挂载）
│   ├── seed.py             # 演示数据（分类、商品、体验账号）
│   └── app/
│       ├── core/config.py  # 配置（pydantic-settings，读 .env）
│       ├── db/database.py  # 引擎 / Session / Base
│       ├── models.py       # ORM 模型
│       ├── schemas.py      # Pydantic 契约（校验器 + 文档）
│       ├── security.py     # bcrypt + JWT
│       ├── services.py     # 订单号（雪花算法）
│       └── router/         # deps / user / product / trade
└── frontend/               # 纯静态页面（index.html + assets）
```

## 快速开始

```bash
# 1. 虚拟环境（Python 3.13）
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt

# 2. 配置：复制 .env.example 到 backend/.env，按需改 MySQL 账号密码
#    没有 MySQL 时，把 DB_URL 设为 sqlite:///./dev.db 也能跑通

# 3. 建库建表（MySQL 方式）
mysql -u root -p < database/init.sql

# 4. 演示数据 + 启动
cd backend
python seed.py
uvicorn main:app --reload --port 8000
```

浏览器访问：`http://127.0.0.1:8000/`（商城首页）、`http://127.0.0.1:8000/docs`（Swagger 在线接口文档）。
体验账号：`demo / 123456`（初始余额 10000 元）。

## 接口一览（前缀 `/api/v1`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| POST | `/users/register` | 注册 |
| POST | `/users/login` | 登录，签发 JWT |
| GET | `/users/me` | 当前登录用户 |
| GET | `/categories` | 分类树（一级 + 二级） |
| GET | `/products` | 商品列表（分页 / 搜索 / 分类筛选 / 排序） |
| GET | `/products/{id}` | 商品详情 |
| POST | `/cart` | 加入购物车（同商品同规格累加） |
| GET | `/cart` | 购物车列表 |
| PATCH | `/cart/{id}` | 改数量 |
| DELETE | `/cart/{id}` | 删除 |
| POST | `/addresses` | 新增地址（默认地址互斥） |
| GET | `/addresses` | 地址列表 |
| POST | `/orders` | 结算下单（扣库存 + 扣余额 + 写流水） |
| GET | `/orders` | 我的订单 |
| POST | `/orders/{id}/cancel` | 取消订单（退余额 + 回滚库存） |
| GET | `/wallet` | 查询余额 |
| POST | `/wallet/recharge` | 充值 |
| GET | `/wallet/logs` | 钱包流水 |

## 设计要点

- **金额一律 DECIMAL(10,2)**，代码里用 `Decimal` 计算，不用 float。
- **订单明细存快照**（名称 / 成交单价 / 规格 / 主图），商品后续改价改名不影响历史订单。
- **软删除**：商品 `status=1/0`、用户 `is_enabled`，不物理删除。
- **接口契约先行**：`app/schemas.py` 里的 Pydantic 模型即契约，`/docs` 自动渲染。
- 前端静态资源最后挂载（catch-all），保证 `/docs`、`/health`、`/api/*` 不被吃掉。
