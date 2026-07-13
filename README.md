# Churn Radar — Customer Churn Prediction Dashboard

Full-stack churn prediction platform: an XGBoost model scores every customer daily,
explains *why* with SHAP, and drives a rule-based intervention queue — built end-to-end
with FastAPI, Next.js, and a real ML pipeline (not a notebook demo).

Trained on the [IBM Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn)
dataset (7,043 customers) — **ROC-AUC 0.84**.

## Highlights

- **Real ML, not a toy model** — XGBoost in a scikit-learn `Pipeline`, evaluated with
  ROC-AUC / F1 / precision / recall, versioned and retrainable from the UI in one click.
- **Explainable, not a black box** — per-customer SHAP contributions precomputed at
  scoring time, ranked and shown in plain language on every customer's page.
- **Automated, not manual** — APScheduler re-scores the entire customer base every night
  at midnight; a rules engine turns risk tier into a concrete next action automatically.
- **Auditable** — every score and every intervention (pending/actioned/dismissed) is
  logged to SQLite, so nothing the dashboard shows is a black box after the fact.

---
## Demo

<video src="https://github.com/user-attachments/assets/ca71d68d-e03d-4d8c-af15-89f6ce7ce766
" controls autoplay loop muted width="100%">
  Your browser does not support the video tag.
</video>

Screen recording (no audio): Navigating the high-level KPI dashboard, analyzing SHAP-driven risk factors for an individual customer, filtering the customer queue, and inspecting ML model evaluation metrics.

## Screenshots

**Dashboard** — portfolio-level KPIs, risk distribution, 30-day churn trend, top-risk queue
![Dashboard](screenshots/dashboard.png)

**Customer detail** — SHAP-driven "why this customer is at risk," ranked and explained
![Customer detail](screenshots/customer-detail.png)

**Customers** — searchable, filterable, sortable table across all 7,043 customers
![Customers list](screenshots/customers-list.png)

**Interventions** — the action queue a CS team actually works from
![Interventions](screenshots/interventions.png)

**Model performance** — ROC-AUC / F1 / precision / recall, feature importance, one-click retrain
![Model performance](screenshots/model-performance.png)

---

## Page tour

| Page | What it shows |
|------|---------------|
| **Dashboard** (`/`) | KPI cards, risk-distribution donut, 30-day churn trend, top-10 risky customers, recent interventions |
| **Customers** (`/customers`) | Searchable, filterable, sortable, paginated table of all 7,043 customers |
| **Customer detail** (`/customers/[id]`) | Churn score, per-customer SHAP drivers, score history, recommendation, intervention log |
| **Interventions** (`/interventions`) | All triggered interventions, filter by status, mark actioned / dismissed |
| **Model** (`/model`) | ROC-AUC / F1 / precision / recall, global feature importance, retrain button |

---

## Architecture

```
                          ┌──────────────────────────────────────────┐
                          │            Next.js 14 (App Router)         │
                          │   Dashboard · Customers · Detail · Model   │
                          │           Tailwind CSS + Recharts          │
                          └────────────────────┬───────────────────────┘
                                               │  REST (JSON)
                                               ▼
                          ┌──────────────────────────────────────────┐
                          │                FastAPI                     │
                          │  /dashboard  /customers  /interventions    │
                          │  /model/metrics  /model/retrain  /scoring  │
                          └───────┬───────────────────────┬────────────┘
                                  │                       │
                     ┌────────────▼─────────┐   ┌─────────▼───────────┐
                     │   ML pipeline         │   │   APScheduler        │
                     │  train.py → model.pkl │   │  daily 00:00 scoring │
                     │  score.py (SHAP)      │   └─────────┬───────────┘
                     │  interventions.py     │             │
                     └────────────┬──────────┘             │
                                  │                        │
                          ┌───────▼────────────────────────▼─────────┐
                          │            SQLite  (SQLAlchemy)            │
                          │  customers · interventions ·               │
                          │  score_history · scoring_runs · model_meta │
                          └────────────────────────────────────────────┘
                                  ▲
                     ┌────────────┴───────────┐
                     │  Kaggle API (IBM Telco) │  ← downloaded at setup
                     └────────────────────────┘
```

**Tech stack:** Next.js 14 · Tailwind CSS · Recharts · FastAPI · SQLAlchemy · SQLite ·
XGBoost · scikit-learn · SHAP · pandas · APScheduler.

### Design decisions

- **SHAP is precomputed at scoring time, not on page load.** Explaining a prediction is
  more expensive than making one; batching it into the nightly job keeps every customer
  page instant instead of running live inference on every click.
- **The intervention rules are separate from the model.** Risk tier → recommended action
  is a small, explicit rules file, not something baked into the model. A business
  stakeholder can change what "High risk" means to do without anyone retraining anything.
- **Training and scoring share one `Pipeline` object.** Preprocessing (scaling, one-hot
  encoding) is fit once during training and serialized with the model, so there's no way
  for train/serve preprocessing to drift out of sync.
- **Re-scoring is idempotent for interventions.** A customer already sitting in a pending
  intervention doesn't get a duplicate one every night — only genuinely new risk creates
  a new action.

---

## Project structure

```
backend/
  main.py            FastAPI app + all routes
  scheduler.py       APScheduler daily scoring job (midnight UTC)
  interventions.py   Rule-based intervention engine
  config.py          Env config + risk-tier thresholds
  schemas.py         Pydantic response models
  ml/
    dataset.py       Kaggle download (+ synthetic fallback)
    features.py      Feature definitions / preprocessing
    train.py         Train XGBoost -> model.pkl + metrics
    score.py         Score all customers + per-customer SHAP drivers
    model.pkl        (generated) trained pipeline bundle
  db/
    database.py      Engine / session / Base
    models.py        ORM models
    seed.py          Load Telco data, score, backfill history, seed interventions
  requirements.txt
  .env.example
frontend/
  app/               page.jsx, customers/, customers/[id]/, model/, interventions/
  components/        KPICard, RiskBadge, ChurnChart, CustomerTable, InterventionFeed, Sidebar
  lib/api.js         API client + formatters
  package.json  tailwind.config.js  .env.example
data/                (generated) telco_churn.csv
README.md
```

---

## Setup & run

### Prerequisites
- Python 3.9+ and Node.js 18+
- (Optional) a Kaggle account for the real dataset — otherwise a realistic synthetic
  dataset with the identical schema is generated automatically.

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # then fill in your Kaggle credentials (see below)

python -m ml.train                  # download data + train model -> ml/model.pkl
python -m db.seed                   # create churn.db, score 7,043 customers, seed history
uvicorn main:app --reload --port 8020
```

The API is now at **http://127.0.0.1:8020** (interactive docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local          # NEXT_PUBLIC_API_BASE=http://127.0.0.1:8020
npm run dev
```

Open **http://localhost:3000**.

---

## Downloading the dataset via the Kaggle API

1. Create a Kaggle API token: **kaggle.com → Account → Settings → Create New Token**.
   This downloads a `kaggle.json` containing your `username` and `key`.
2. Put the credentials in `backend/.env`:

   ```env
   KAGGLE_USERNAME=your_kaggle_username
   KAGGLE_KEY=your_kaggle_key
   ```
3. `python -m ml.train` (or `python -m ml.dataset --download`) will then run the
   equivalent of:

   ```bash
   kaggle datasets download -d blastchar/telco-customer-churn
   ```

   and unzip it to `data/telco_churn.csv`.

> **No Kaggle account?** No problem — if credentials are missing or offline, the loader
> automatically generates a synthetic 7,043-row dataset with the exact Telco schema and
> realistic churn relationships, so the app runs end-to-end without any external calls.

---

## Manually triggering scoring & retraining

**From the UI:** the Dashboard has a **“Run scoring now”** button; the Model page has a
**“Retrain model”** button (with a confirmation modal).

**From the API:**

```bash
# Re-score every customer with the current model (also refreshes interventions)
curl -X POST http://127.0.0.1:8020/api/scoring/run

# Retrain XGBoost on the full dataset, then re-score everyone
curl -X POST http://127.0.0.1:8020/api/model/retrain
```

**From the CLI:**

```bash
cd backend && source venv/bin/activate
python -m ml.train          # retrain -> model.pkl + new model_metadata row
python -m ml.score          # score all customers in the DB
python -m scheduler         # run the daily scoring job once, on demand
```

**Automatically:** APScheduler runs the scoring pipeline every day at **00:00 UTC** while
the FastAPI server is running.

---

## How scoring & interventions work

- **Risk tiers:** Low `0–30%`, Medium `30–60%`, High `60–100%` churn probability.
- **Per-customer drivers:** at scoring time we precompute each customer's top churn
  drivers using XGBoost SHAP contributions and store them on the row — so the detail page
  is instant, never computing on demand.
- **Intervention rules:**
  - **High (>60%)** → flag for immediate outreach + suggest a personalized retention discount.
  - **Medium (30–60%)** → suggest a check-in call + highlight unused features.
  - **Low (<30%)** → monitor only, no action.
  - Re-scoring never creates duplicate open interventions for the same customer.

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/summary` | Totals, risk counts, avg probability, week-over-week trend |
| GET | `/api/dashboard/trend?days=30` | Daily avg churn probability + tier counts |
| GET | `/api/customers` | Paginated list — `tier`, `search`, `sort`, `order`, `page`, `page_size` |
| GET | `/api/customers/{id}` | Detail: features, SHAP drivers, score history, interventions |
| POST | `/api/customers/{id}/interventions` | Manually trigger an intervention |
| GET | `/api/interventions?status=pending` | List interventions, filterable by status |
| PATCH | `/api/interventions/{id}` | Update status (`pending`/`actioned`/`dismissed`) |
| GET | `/api/model/metrics` | ROC-AUC, F1, precision, recall, feature importances |
| POST | `/api/model/retrain` | Retrain + re-score |
| POST | `/api/scoring/run` | Re-score all customers now |

---

## Example use cases

- **Customer Success Manager** opens the Dashboard each morning, sees the 1,000+ high-risk
  accounts, and works the **Interventions** queue — calling flagged customers and marking
  each one *actioned*.
- **Business owner** checks the 30-day churn trend and risk-distribution donut to gauge
  whether retention is improving, without needing to read any code or SQL.
- **Ops / analyst** opens a customer's detail page before a renewal call to see exactly
  *which factors* (month-to-month contract, no tech support, high monthly charges…) are
  driving that account's risk, and follows the recommended action.
- **Data owner** retrains the model from the Model page after new data lands and confirms
  ROC-AUC / precision / recall are still healthy.

---

## Environment variables

**backend/.env**

```env
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_key
DATABASE_URL=sqlite:///./churn.db
MODEL_PATH=ml/model.pkl
FRONTEND_ORIGIN=http://localhost:3000
```

**frontend/.env.local**

```env
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8020
```
