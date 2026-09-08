# Functional Requirements — Eyeglasses Listing Demo

Reference document capturing everything agreed on for this project so future work doesn't have to re-derive it. Source: Lenskart "All Eyeglasses" listing page (`lenskart.com/eyeglasses/promotions/all-eyeglasses.html`).

## 1. Project scope

A learning/demo build, not a production e-commerce system. Four tasks:

- **Task 1** — Frontend UI (HTML/CSS/JS)
- **Task 2** — Backend API (Python)
- **Task 3** — Docker & DevOps integration
- **Task 4** — Data analytics with pandas

Explicitly **out of scope**: authentication, database persistence, payments, cloud/Kubernetes deployment. Stays a read-only product catalog demo on a single host.

## 2. Task 1 — Frontend

**Location:** `frontend/index.html` (+ `config.js`, `config.template.js`)

Replicates the structure of the reference page:

- Header with logo and primary nav (Eyeglasses, Sunglasses, Contacts, Special Power)
- Breadcrumb trail
- Filters sidebar (Price, Gender, Shape & Style, Frame Size, Brand, Frame Color, Material — display only, non-functional in this demo)
- Sort control (`Recommended`, `Price: Low to High`, `Price: High to Low`, `Rating`)
- Product grid, one card per item, each showing:
  - Brand name
  - Product name
  - Star rating
  - Discounted price, strikethrough original price, discount %
  - Promo code badge ("Use code SINGLE for this price")
  - Color-variant count badge (e.g. "+4 colors")
- Item count ("N items found")
- Loading / error state when the backend is unreachable

**Data source:** fetched live from the Task 2 API via `fetch()` — no hardcoded product data in the frontend. API base URL is configurable via `window.API_BASE` (set by `config.js` locally, or injected by the Docker container at startup).

**Images:** placeholder images (placehold.co) stand in for real product photography — no scraping of Lenskart's actual assets.

## 3. Task 2 — Backend

**Location:** `backend/app.py` (Flask), `backend/requirements.txt`

**Data:** an in-memory, hand-written list of mock products (4 items) — not scraped from the live Lenskart site. Each product has: `id`, `brand`, `name`, `image`, `rating`, `price`, `original_price`, `discount_pct`, `promo_code`, `colors`.

**Endpoints:**

| Method | Path | Query params | Behavior |
|---|---|---|---|
| GET | `/api/products` | `brand` (optional), `sort` (`price_low_high`, `price_high_low`, `rating`) | Returns `{count, products[]}`, filtered/sorted server-side |
| GET | `/api/products/<id>` | — | Returns one product, or `404 {"error": "Product not found"}` |

CORS enabled (`flask-cors`) so the frontend can call it from a different origin/port. Binds to `0.0.0.0:5000` so it's reachable from outside its container.

## 4. Task 3 — Docker & DevOps

**Location:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `.github/workflows/docker-ci.yml`

- **Backend image:** `python:3.12-slim`, installs `requirements.txt`, exposes `5000`, container healthcheck hits `/api/products`.
- **Frontend image:** `nginx:1.27-alpine`, serves `index.html`, exposes `80` (mapped to host `8080`). `API_BASE` is passed as an environment variable and rendered into `config.js` via `envsubst` at container start — no rebuild needed to repoint the frontend at a different backend.
- **docker-compose.yml:** starts both services on a shared bridge network (`lenskart-net`); frontend's `depends_on` waits for the backend's healthcheck to pass.
- **CI (`docker-ci.yml`):** on push/PR to `main` — `docker compose build`, `docker compose up -d`, poll the backend until healthy, curl-smoke-test both services, then tear down.

**Environment assumption:** a Docker daemon (Docker Desktop or equivalent) is available wherever this is built/run. In this project's own dev sandbox no daemon was present, so only `docker compose config` (static validation) was run — an actual `docker compose up` has not yet been verified and should be the first thing confirmed in any environment with Docker available.

## 5. Task 4 — Data analytics with pandas

**Status: executed.** Implemented directly against this spec in the same session it was added.

**Location:** `backend/analytics.py`, `backend/app.py` (`GET /api/analytics`), `frontend/index.html` ("Catalog analytics" panel).

**Scope:** summarize the existing product catalog with `pandas` — no new data source, just aggregates over the same `PRODUCTS` list used by `/api/products`. Read-only, computed on demand, no caching layer (not needed at 4-item scale).

**Backend:**
- `build_dataframe(products)` — list of product dicts → `pandas.DataFrame`.
- `summarize(products)` — returns:
  - `price` / `discount_pct` / `rating` — min, max, mean (+ median for price)
  - `brand_breakdown` — per-brand count, avg price, avg rating via `groupby("brand").agg(...)`
  - `price_distribution` — item counts across price bands (`<1500`, `1500-2000`, `2000-2500`, `2500+`) via `pd.cut`
  - `top_rated` / `best_discount` — top 3 products by rating / by discount %
- New endpoint: `GET /api/analytics` (no params) → `summarize(PRODUCTS)`.
- New dependency: `pandas==2.2.3` in `backend/requirements.txt`.

**Frontend:** a "Catalog analytics" section below the product grid — four stat tiles (Avg Price, Avg Discount, Avg Rating, Price Range) plus a per-brand table (brand, item count, avg price, avg rating). Fetched independently of the product grid so a slow/failed analytics call never blocks the listing; degrades to an inline "Analytics unavailable" message on error.

**Execution evidence:**
- `curl http://127.0.0.1:5000/api/analytics` returned computed stats matching the 4-item mock catalog: avg price ₹1787.5, avg discount 25.5%, avg rating 4.74, per-brand breakdown for Vincent Chase (2 items, ₹1575 avg) / Lenskart Air / John Jacobs.
- Frontend screenshot (localhost:8080) confirmed the same numbers rendering live in the "Catalog analytics" panel, sourced from that endpoint — not hardcoded.

## 6. Evidence & reporting requirements

Each task's completion is documented in `evidence.html` (published as a Claude artifact), which must include:

- An architecture diagram (frontend ↔ backend ↔ data, and separately the container/network/CI topology for Task 3)
- Live proof, not just code: actual curl output / API responses, and a live-rendered screenshot of the frontend pulling real data from the backend
- Clear labeling of anything that could not be verified in the current environment (e.g. Docker build/run), rather than presenting untested config as tested

## 7. Decided defaults (formerly open questions)

These were ambiguous at project start and have since been settled as explicit requirements, so they should be treated as fixed unless the user says otherwise:

- No auth, database, or payment flow — read-only catalog only.
- Mock data and placeholder images are acceptable substitutes for Lenskart's real catalog and assets.
- "DevOps integration" means containerize + Compose + basic CI — not a cloud/Kubernetes rollout.
- A published HTML report with diagrams is the expected evidence format, not raw terminal logs alone.
- If a build/run step can't be executed in the current environment (e.g. no Docker daemon), that must be stated explicitly rather than assumed to have passed.
- Analytics (Task 4) stay aggregate-only and computed on-demand — no caching, no per-user or time-series analysis, since there's no user/event data in this project.

## 8. Still open

- No stated grading rubric or external success criteria beyond what's captured in §6 — if this maps to a course assignment or interview task, the actual rubric isn't known.
- Copyright/ToS constraints on how closely the UI may resemble Lenskart's real branding, beyond generic layout inspiration, haven't been specified.
- Whether this ever needs to run in an environment with a real Docker daemon has not been confirmed — Task 3's container build/run is still unverified end-to-end.
- Whether Task 3's CI workflow should also smoke-test `/api/analytics` — not yet added to `docker-ci.yml`.
- Whether a larger, non-mock dataset is expected before Task 4 counts as "real" analytics rather than a proof of concept.
