"""FastAPI application exposing the churn dashboard API."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import FRONTEND_ORIGIN, risk_tier
from db.database import get_db, init_db
from db.models import (
    Customer,
    Intervention,
    ModelMetadata,
    ScoreHistory,
    ScoringRun,
)
from interventions import recommend
from schemas import (
    CustomerDetail,
    CustomerList,
    CustomerRow,
    DashboardSummary,
    InterventionOut,
    InterventionStatusUpdate,
    ModelMetrics,
    TrendPoint,
)

app = FastAPI(title="Customer Churn Prediction Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SORTABLE = {
    "churn_probability": Customer.churn_probability,
    "tenure": Customer.tenure,
    "monthly_charges": Customer.monthly_charges,
    "name": Customer.name,
    "last_scored": Customer.last_scored,
    "risk_tier": Customer.risk_tier,
}


@app.on_event("startup")
def _startup():
    init_db()
    # Start the daily scoring scheduler (guarded so tests/imports don't double-start).
    try:
        from scheduler import start_scheduler

        start_scheduler()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] Scheduler not started: {exc}")


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@app.get("/api/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(Customer.id)).scalar() or 0
    counts = dict(
        db.query(Customer.risk_tier, func.count(Customer.id))
        .group_by(Customer.risk_tier)
        .all()
    )
    avg_prob = db.query(func.avg(Customer.churn_probability)).scalar() or 0.0

    # Trend vs ~7 days ago using the ScoringRun log.
    week_ago = datetime.utcnow() - timedelta(days=7)
    prev_run = (
        db.query(ScoringRun)
        .filter(ScoringRun.timestamp <= week_ago)
        .order_by(ScoringRun.timestamp.desc())
        .first()
    )
    latest_meta = (
        db.query(ModelMetadata).order_by(ModelMetadata.id.desc()).first()
    )
    last_scored = db.query(func.max(Customer.last_scored)).scalar()
    pending = (
        db.query(func.count(Intervention.id))
        .filter(Intervention.status == "pending")
        .scalar()
        or 0
    )

    avg_prob = round(float(avg_prob), 4)
    resp = DashboardSummary(
        total_customers=total,
        high_risk=counts.get("High", 0),
        medium_risk=counts.get("Medium", 0),
        low_risk=counts.get("Low", 0),
        avg_churn_probability=avg_prob,
        pending_interventions=pending,
        last_scored=last_scored,
        model_version=latest_meta.model_version if latest_meta else None,
    )
    if prev_run:
        resp.avg_prob_last_week = prev_run.avg_probability
        resp.avg_prob_trend = round(avg_prob - prev_run.avg_probability, 4)
        resp.high_risk_last_week = prev_run.high_count
        resp.high_risk_trend = counts.get("High", 0) - prev_run.high_count
    return resp


@app.get("/api/dashboard/trend", response_model=list[TrendPoint])
def dashboard_trend(days: int = Query(30, ge=1, le=90), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(ScoringRun)
        .filter(ScoringRun.timestamp >= since)
        .order_by(ScoringRun.timestamp.asc())
        .all()
    )
    return [
        TrendPoint(
            date=r.timestamp.strftime("%Y-%m-%d"),
            avg_probability=r.avg_probability or 0.0,
            high=r.high_count or 0,
            medium=r.medium_count or 0,
            low=r.low_count or 0,
        )
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# Customers
# --------------------------------------------------------------------------- #
@app.get("/api/customers", response_model=CustomerList)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    tier: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("churn_probability"),
    order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    q = db.query(Customer)
    if tier and tier.lower() != "all":
        q = q.filter(Customer.risk_tier == tier.capitalize())
    if search:
        like = f"%{search}%"
        q = q.filter((Customer.name.ilike(like)) | (Customer.id.ilike(like)))

    total = q.count()
    sort_col = SORTABLE.get(sort, Customer.churn_probability)
    sort_col = sort_col.desc() if order == "desc" else sort_col.asc()
    rows = (
        q.order_by(sort_col)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        CustomerRow(
            id=c.id,
            name=c.name,
            tenure=c.tenure,
            contract=c.contract,
            monthly_charges=c.monthly_charges,
            churn_probability=c.churn_probability or 0.0,
            risk_tier=c.risk_tier or "Low",
            last_scored=c.last_scored,
        )
        for c in rows
    ]
    return CustomerList(total=total, page=page, page_size=page_size, items=items)


@app.get("/api/customers/{customer_id}", response_model=CustomerDetail)
def customer_detail(customer_id: str, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    contributions = json.loads(c.feature_contributions) if c.feature_contributions else []
    history = (
        db.query(ScoreHistory)
        .filter(ScoreHistory.customer_id == customer_id)
        .order_by(ScoreHistory.scored_date.asc())
        .all()
    )
    interventions = (
        db.query(Intervention)
        .filter(Intervention.customer_id == customer_id)
        .order_by(Intervention.triggered_date.desc())
        .all()
    )

    detail = CustomerDetail.model_validate(
        {
            **{k: getattr(c, k) for k in CustomerDetail.model_fields
               if hasattr(c, k) and k not in
               ("feature_contributions", "score_history", "interventions",
                "current_recommendation")},
            "feature_contributions": contributions,
            "score_history": [
                {
                    "scored_date": h.scored_date,
                    "churn_probability": h.churn_probability,
                    "risk_tier": h.risk_tier,
                }
                for h in history
            ],
            "interventions": [_intervention_out(i, c.name) for i in interventions],
            "current_recommendation": recommend(c.risk_tier, c),
        }
    )
    return detail


# --------------------------------------------------------------------------- #
# Interventions
# --------------------------------------------------------------------------- #
def _intervention_out(i: Intervention, customer_name: str | None = None) -> dict:
    return {
        "id": i.id,
        "customer_id": i.customer_id,
        "customer_name": customer_name,
        "intervention_type": i.intervention_type,
        "recommendation": i.recommendation,
        "risk_tier": i.risk_tier,
        "churn_probability": i.churn_probability,
        "triggered_date": i.triggered_date,
        "status": i.status,
    }


@app.get("/api/interventions", response_model=list[InterventionOut])
def list_interventions(
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Intervention, Customer.name).join(
        Customer, Customer.id == Intervention.customer_id
    )
    if status and status.lower() != "all":
        q = q.filter(Intervention.status == status.lower())
    rows = q.order_by(Intervention.triggered_date.desc()).limit(limit).all()
    return [_intervention_out(i, name) for i, name in rows]


@app.patch("/api/interventions/{intervention_id}", response_model=InterventionOut)
def update_intervention(
    intervention_id: int,
    payload: InterventionStatusUpdate,
    db: Session = Depends(get_db),
):
    if payload.status not in ("pending", "actioned", "dismissed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    i = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Intervention not found")
    i.status = payload.status
    db.commit()
    db.refresh(i)
    name = db.query(Customer.name).filter(Customer.id == i.customer_id).scalar()
    return _intervention_out(i, name)


@app.post("/api/customers/{customer_id}/interventions", response_model=InterventionOut)
def create_manual_intervention(customer_id: str, db: Session = Depends(get_db)):
    """Manually trigger an intervention for a customer (used by the detail page)."""
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    rec = recommend(c.risk_tier, c) or {
        "intervention_type": "Manual review",
        "recommendation": f"Manual review requested for {c.name}.",
    }
    i = Intervention(
        customer_id=c.id,
        intervention_type=rec["intervention_type"],
        recommendation=rec["recommendation"],
        risk_tier=c.risk_tier,
        churn_probability=c.churn_probability,
        triggered_date=datetime.utcnow(),
        status="pending",
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    return _intervention_out(i, c.name)


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #
@app.get("/api/model/metrics", response_model=ModelMetrics)
def model_metrics(db: Session = Depends(get_db)):
    meta = db.query(ModelMetadata).order_by(ModelMetadata.id.desc()).first()
    if not meta:
        raise HTTPException(status_code=404, detail="No trained model metadata found")
    importances = json.loads(meta.feature_importances) if meta.feature_importances else []
    return ModelMetrics(
        model_version=meta.model_version,
        training_date=meta.training_date,
        roc_auc=meta.roc_auc,
        f1=meta.f1,
        precision=meta.precision,
        recall=meta.recall,
        accuracy=meta.accuracy,
        n_train=meta.n_train,
        n_test=meta.n_test,
        feature_importances=importances,
    )


@app.post("/api/model/retrain")
def retrain(db: Session = Depends(get_db)):
    """Retrain the model, then re-score every customer with the fresh model."""
    from ml.score import load_model
    from ml.train import train_model

    result = train_model(persist_metadata=True)
    load_model(force_reload=True)  # drop cached old model

    from ml.score import score_all_customers

    scoring = score_all_customers(db)
    return {"training": result, "scoring": scoring}


@app.post("/api/scoring/run")
def run_scoring(db: Session = Depends(get_db)):
    from ml.score import score_all_customers

    return score_all_customers(db)
