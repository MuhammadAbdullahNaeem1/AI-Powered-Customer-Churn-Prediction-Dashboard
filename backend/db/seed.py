"""Seed the database from the Telco dataset.

Steps:
  1. Create tables.
  2. Insert all ~7,043 customers with their real feature values + a generated name.
  3. Score every customer with the trained model (writes today's ScoreHistory + a ScoringRun).
  4. Backfill 30 days of synthetic score history + daily ScoringRun summaries so the
     dashboard trend charts are populated on first load.
  5. Generate synthetic intervention history (varied statuses/dates) for the top 200
     highest-risk customers.

Idempotent-ish: running again wipes and repopulates the customer-derived tables.
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import risk_tier  # noqa: E402
from db.database import Base, SessionLocal, engine, init_db  # noqa: E402
from db.models import (  # noqa: E402
    Customer,
    Intervention,
    ScoreHistory,
    ScoringRun,
)
from interventions import recommend  # noqa: E402
from ml.dataset import load_dataset  # noqa: E402
from ml.features import clean_raw_dataframe  # noqa: E402
from ml.score import score_all_customers  # noqa: E402

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Chris", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Sandra", "Mark", "Ashley", "Donald", "Kimberly",
    "Steven", "Emily", "Paul", "Donna", "Andrew", "Michelle", "Joshua", "Carol",
    "Amara", "Wei", "Priya", "Diego", "Fatima", "Hassan", "Yuki", "Ana", "Omar", "Sofia",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Patel", "Kim", "Okafor", "Ali", "Cohen", "Rossi", "Silva", "Chen", "Khan", "Nakamura",
]


def _name_for(customer_id: str) -> str:
    rng = random.Random(customer_id)
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _reset_tables():
    Base.metadata.drop_all(bind=engine)
    init_db()


def _insert_customers(db) -> int:
    df = clean_raw_dataframe(load_dataset())
    objects = []
    for _, r in df.iterrows():
        objects.append(
            Customer(
                id=str(r["customerID"]),
                name=_name_for(str(r["customerID"])),
                gender=r["gender"],
                senior_citizen=int(r["SeniorCitizen"]),
                partner=r["Partner"],
                dependents=r["Dependents"],
                tenure=int(r["tenure"]),
                phone_service=r["PhoneService"],
                multiple_lines=r["MultipleLines"],
                internet_service=r["InternetService"],
                online_security=r["OnlineSecurity"],
                online_backup=r["OnlineBackup"],
                device_protection=r["DeviceProtection"],
                tech_support=r["TechSupport"],
                streaming_tv=r["StreamingTV"],
                streaming_movies=r["StreamingMovies"],
                contract=r["Contract"],
                paperless_billing=r["PaperlessBilling"],
                payment_method=r["PaymentMethod"],
                monthly_charges=float(r["MonthlyCharges"]),
                total_charges=float(r["TotalCharges"]),
                churn_label=r.get("Churn"),
            )
        )
    db.bulk_save_objects(objects)
    db.commit()
    return len(objects)


def _backfill_history(db, days: int = 30):
    """Create synthetic prior-day score history + ScoringRun summaries.

    We anchor on each customer's current probability and add small daily noise,
    with a gentle upward drift into the present so the trend line looks organic.
    """
    customers = db.query(Customer).all()
    rng = np.random.default_rng(7)
    today = datetime.utcnow().replace(hour=0, minute=5, second=0, microsecond=0)
    model_version = _latest_version(db)

    history_objs = []
    for day in range(days, 0, -1):
        ts = today - timedelta(days=day)
        drift = -0.03 * (day / days)  # slightly lower in the past -> rising trend
        counts = {"High": 0, "Medium": 0, "Low": 0}
        day_probs = []
        for c in customers:
            base = c.churn_probability if c.churn_probability is not None else 0.2
            noise = float(rng.normal(0, 0.03))
            p = min(max(base + drift + noise, 0.0), 1.0)
            tier = risk_tier(p)
            counts[tier] += 1
            day_probs.append(p)
            history_objs.append(
                ScoreHistory(
                    customer_id=c.id,
                    churn_probability=round(p, 4),
                    risk_tier=tier,
                    scored_date=ts,
                )
            )
        db.add(
            ScoringRun(
                timestamp=ts,
                total_scored=len(customers),
                high_count=counts["High"],
                medium_count=counts["Medium"],
                low_count=counts["Low"],
                avg_probability=round(float(np.mean(day_probs)), 4),
                model_version=model_version or "seed",
            )
        )
    db.bulk_save_objects(history_objs)
    db.commit()


def _latest_version(db) -> str:
    from db.models import ModelMetadata

    row = db.query(ModelMetadata).order_by(ModelMetadata.id.desc()).first()
    return row.model_version if row else "seed"


def _persist_model_metadata(db):
    """Write ModelMetadata from the trained model.pkl bundle.

    Training writes this row too, but seed drops all tables on reset, so we
    re-materialize it here from the saved bundle instead of retraining.
    """
    import json

    from db.models import ModelMetadata
    from ml.score import load_model

    bundle = load_model(force_reload=True)
    m = bundle.get("metrics", {})
    db.add(
        ModelMetadata(
            model_version=bundle.get("version", "seed"),
            training_date=datetime.utcnow(),
            roc_auc=m.get("roc_auc"),
            f1=m.get("f1"),
            precision=m.get("precision"),
            recall=m.get("recall"),
            accuracy=m.get("accuracy"),
            feature_importances=json.dumps(bundle.get("importances", [])),
            n_train=bundle.get("n_train"),
            n_test=bundle.get("n_test"),
        )
    )
    db.commit()


def _seed_interventions(db, top_n: int = 200):
    """Synthetic intervention history for the top-N riskiest customers."""
    db.query(Intervention).delete()
    db.commit()

    top = (
        db.query(Customer)
        .order_by(Customer.churn_probability.desc())
        .limit(top_n)
        .all()
    )
    rng = random.Random(123)
    statuses = ["pending", "actioned", "dismissed"]
    weights = [0.5, 0.35, 0.15]
    now = datetime.utcnow()

    for cust in top:
        rec = recommend(cust.risk_tier, cust)
        if not rec:
            continue
        # 1–2 historical interventions per top customer.
        for _ in range(rng.randint(1, 2)):
            status = rng.choices(statuses, weights)[0]
            days_ago = rng.randint(0, 25)
            db.add(
                Intervention(
                    customer_id=cust.id,
                    intervention_type=rec["intervention_type"],
                    recommendation=rec["recommendation"],
                    risk_tier=cust.risk_tier,
                    churn_probability=cust.churn_probability,
                    triggered_date=now - timedelta(days=days_ago, hours=rng.randint(0, 23)),
                    status=status,
                )
            )
    db.commit()


def seed():
    _reset_tables()
    db = SessionLocal()
    try:
        n = _insert_customers(db)
        print(f"[seed] Inserted {n} customers.")

        _persist_model_metadata(db)
        print("[seed] Persisted model metadata from bundle.")

        summary = score_all_customers(db, trigger_interventions=False)
        print(f"[seed] Scored customers: {summary}")

        _backfill_history(db)
        print("[seed] Backfilled 30 days of score history.")

        _seed_interventions(db)
        n_int = db.query(Intervention).count()
        print(f"[seed] Generated {n_int} synthetic interventions.")
    finally:
        db.close()
    print("[seed] Done.")


if __name__ == "__main__":
    seed()
