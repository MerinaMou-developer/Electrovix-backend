## Electrovix Backend – Django REST API + AI Product Search

Electrovix backend is a production‑style **Django REST Framework** API that powers the Electrovix e‑commerce platform: products, categories/brands, users & JWT auth, orders/checkout, payment integration, and an AI‑assisted product discovery experience using **vector search (pgvector)**.

### 🌐 Live API

- **Base URL**: [`https://electrovix-backend.onrender.com`](https://electrovix-backend.onrender.com)
- **API prefix**: `/api`

---

### 🧰 Tech Stack

- **Framework**: Django + Django REST Framework
- **Auth**: JWT (`djangorestframework-simplejwt`)
- **Database**: PostgreSQL
- **Vector search**: `pgvector` (Product embeddings stored in Postgres)
- **Semantic embeddings**: `sentence-transformers` + PyTorch (CPU wheels)
- **Payments**: SSLCommerz (`sslcommerz-lib`)
- **Email**: SMTP (Gmail) for account activation
- **Deployment**: Gunicorn + WhiteNoise (static) + Render
- **Docker**: `Dockerfile` + `docker-compose.yml` (includes pgvector image)

---

### ✨ What This Backend Does

- **Products & catalog**
  - List products with **search + pagination**.
  - Filter by **category**, **brand**, and **min/max price**.
  - Sort modes like **best seller**, **featured**, **latest**, and **discount**.
  - Top products endpoint for homepage carousels.
  - Image upload endpoint for products.

- **Reviews**
  - Authenticated users can create reviews.
  - Prevents duplicate reviews per user per product.
  - Auto-updates product rating and review count.

- **Users & authentication**
  - JWT login.
  - Registration with **email activation** (creates inactive user, sends activation link).
  - Profile read/update.
  - Admin endpoints for user list, update, and delete.

- **Orders & checkout**
  - Create orders with shipping address and order items.
  - Stock reduction during order creation.
  - User orders list (paginated) + admin orders list (paginated).
  - Mark orders paid/delivered.

- **Payments (SSLCommerz)**
  - Initiate payment session and store `transaction_id`.
  - Success/fail/cancel callbacks to update order status and redirect to the frontend.

- **AI assistant (hybrid + semantic retrieval)**
  - AI chat endpoint that returns:
    - a helpful answer,
    - detected intent (recommend / compare / budget / search),
    - recommended product IDs,
    - matching product list.
  - Uses **keyword search first**, then **semantic similarity** fallback (Cosine distance on pgvector embeddings).
  - Includes domain re-ranking (example: phone queries ranked above accessories like headphones).

---

### 🔌 API Routes (high level)

All routes are under the live base URL + `/api/...`

#### Products

- `GET /api/products/` – list products (supports filters/query params)
- `GET /api/products/top/` – top products
- `GET /api/products/categories/` – list categories
- `GET /api/products/brand/` – list brands
- `GET /api/products/<id>/` – product details
- `POST /api/products/<id>/reviews/` – create review (auth required)
- `GET /api/products/search/?q=...` – hybrid keyword + semantic search
- `POST /api/products/upload/` – upload product image (admin typically)
- `POST /api/products/create/` – create placeholder product (admin)
- `PUT /api/products/update/<id>/` – update product (admin)
- `DELETE /api/products/delete/<id>/` – delete product (admin)

#### Users

- `POST /api/users/login/` – JWT login
- `POST /api/users/register/` – register + send activation email
- `GET /api/users/activate/<uid>/<token>/` – activate account
- `GET /api/users/profile/` – current user profile (auth)
- `PUT /api/users/profile/update/` – update profile (auth)
- `GET /api/users/` – list users (admin)
- `GET /api/users/<id>/` – user details (admin)
- `PUT /api/users/update/<id>/` – update user (admin)
- `DELETE /api/users/delete/<id>/` – delete user (admin)

#### Orders / Payments

- `POST /api/orders/add/` – create order (auth)
- `GET /api/orders/myorders/` – current user orders (auth)
- `GET /api/orders/<id>/` – order details (auth: owner or admin)
- `PUT /api/orders/<id>/pay/` – mark paid (auth)
- `PUT /api/orders/<id>/deliver/` – mark delivered (admin)
- `POST /api/orders/initiate-payment/` – SSLCommerz session creation (auth)
- `POST /api/orders/payment-success/` – SSLCommerz success callback
- `POST /api/orders/payment-fail/` – SSLCommerz fail callback
- `POST /api/orders/payment-cancel/` – SSLCommerz cancel callback

#### AI

- `POST /api/ai/chat/` – AI shopping assistant chat

---

### 📦 Installation (Local Development)

#### 1) Clone

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>/backend
```

#### 2) Create a virtual environment + install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### 3) Configure environment variables

This backend uses a `.env` file (loaded from `backend/.env`) and expects Postgres + email + payment credentials. See **Environment Variables** below.

#### 4) Run migrations + start the server

```bash
python manage.py migrate
python manage.py runserver 8000
```

API will be available at `http://127.0.0.1:8000/api/`.

---

### 🐳 Docker (Recommended for full stack local)

This repo includes `docker-compose.yml` that runs:

- `web` (Django/Gunicorn)
- `db` (PostgreSQL with pgvector: `pgvector/pgvector:pg15`)

From the `backend` directory:

```bash
docker compose up --build
```

---

### 🔧 Environment Variables (important)

Typical required variables:

- **Django**
  - `SECRET_KEY`
  - `DEBUG` (recommended `False` in production)
  - `PORT` (Render sets this automatically)

- **Database (PostgreSQL)**
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
  - `DB_SSLMODE` (optional; defaults to `disable`)

- **Email (activation)**
  - `EMAIL`
  - `EMAIL_PASSWORD`

- **SSLCommerz**
  - `STORE_ID`
  - `STORE_PASS`
  - `ISSANDBOX` (boolean)
  - `SUCCESS_URL`, `FAIL_URL`, `CANCEL_URL`

Note: The activation email and payment callbacks redirect to the frontend URL. If your frontend domain changes, update those redirect/activation URLs accordingly.

---

### 🧠 AI Semantic Search (How it works)

- Products store a **384‑dimension embedding** (`embedding` field) using `sentence-transformers/all-MiniLM-L6-v2`.
- `GET /api/products/search/?q=...` performs:
  - keyword retrieval first, then semantic similarity fallback via `CosineDistance` on pgvector.
- `POST /api/ai/chat/` builds on that retrieval and returns a human-friendly answer plus matching products.

#### Re-index embeddings

After seeding products (or when you change product text), generate vectors:

```bash
python manage.py reindex_embeddings
```

---

### 🌱 Seed Demo Data

This backend includes a seeding command that creates categories, brands, a demo user, and products (including extra items for semantic search testing):

```bash
python manage.py seed_products
```

Optional (wipe and re-seed):

```bash
python manage.py seed_products --clear
```

---

### 🌐 Production Deployment Notes (Render)

The production server uses **Gunicorn** and can collect static files via **WhiteNoise**.

- **Live backend**: [`https://electrovix-backend.onrender.com`](https://electrovix-backend.onrender.com)
- Ensure Render environment variables are set for:
  - DB connection
  - `SECRET_KEY`
  - email credentials
  - SSLCommerz credentials + callback URLs

The provided `Dockerfile` runs migrations, collects static, seeds products, and starts Gunicorn.

