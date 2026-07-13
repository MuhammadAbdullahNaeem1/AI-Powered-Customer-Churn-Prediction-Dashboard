"""Daily scoring pipeline.

Loads the trained pipeline, scores every customer in the database, updates their
churn probability / risk tier, records a ScoreHistory point, logs a ScoringRun,
and precomputes each customer's top churn drivers (via XGBoost SHAP contributions)
so the detail page never has to compute them on demand.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import MODEL_PATH, risk_tier  # noqa: E402
from ml.features import (  # noqa: E402
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    FRIENDLY_LABELS,
    NUMERIC_FEATURES,
    customers_to_feature_frame,
)

_MODEL_CACHE: dict | None = None


def load_model(force_reload: bool = False) -> dict:
    global _MODEL_CACHE
    if _MODEL_CACHE is None or force_reload:
        if not Path(MODEL_PATH).exists():
            raise FileNotFoundError(
                f"Model artifact not found at {MODEL_PATH}. Run ml/train.py first."
            )
        _MODEL_CACHE = joblib.load(MODEL_PATH)
    return _MODEL_CACHE


def _source_feature(colname: str) -> str:
    if colname in NUMERIC_FEATURES:
        return colname
    for c in CATEGORICAL_FEATURES:
        if colname.startswith(c + "_"):
            return c
    return colname


def _per_customer_drivers(bundle, X, top_k: int = 6) -> list[list[dict]]:
    """Return, for each row, a ranked list of top churn drivers with signed impact.

    Uses XGBoost's exact per-feature SHAP contributions (pred_contribs) on the
    transformed matrix, then aggregates one-hot columns back to source features.
    """
    pipeline = bundle["pipeline"]
    pre = pipeline.named_steps["preprocess"]
    booster = pipeline.named_steps["model"].get_booster()

    import xgboost as xgb

    Xt = pre.transform(X)
    transformed_names = list(pre.get_feature_names_out())
    # ColumnTransformer prefixes names ("num__tenure", "cat__Contract_Yes"); strip it.
    clean_names = [n.split("__", 1)[-1] for n in transformed_names]

    dmat = xgb.DMatrix(Xt, feature_names=[f"f{i}" for i in range(Xt.shape[1])])
    contribs = booster.predict(dmat, pred_contribs=True)  # (n, n_features + 1)

    results: list[list[dict]] = []
    for row in contribs:
        grouped: dict[str, float] = defaultdict(float)
        for name, val in zip(clean_names, row[:-1]):  # last col is bias
            grouped[_source_feature(name)] += float(val)
        ranked = sorted(grouped.items(), key=lambda kv: abs(kv[1]), reverse=True)
        results.append(
            [
                {
                    "feature": src,
                    "label": FRIENDLY_LABELS.get(src, src),
                    "impact": round(val, 4),
                    "direction": "increases" if val > 0 else "reduces",
                }
                for src, val in ranked[:top_k]
            ]
        )
    return results


def score_all_customers(db, trigger_interventions: bool = True) -> dict:
    from db.models import Customer, ScoreHistory, ScoringRun

    bundle = load_model()
    version = bundle.get("version", "unknown")

    customers = db.query(Customer).all()
    if not customers:
        return {"total_scored": 0, "message": "No customers to score."}

    X = customers_to_feature_frame(customers)[FEATURE_COLUMNS]
    probs = bundle["pipeline"].predict_proba(X)[:, 1]
    drivers = _per_customer_drivers(bundle, X)

    now = datetime.utcnow()
    counts = {"High": 0, "Medium": 0, "Low": 0}

    for cust, prob, drv in zip(customers, probs, drivers):
        prob = float(prob)
        tier = risk_tier(prob)
        counts[tier] += 1
        cust.churn_probability = round(prob, 4)
        cust.risk_tier = tier
        cust.last_scored = now
        cust.feature_contributions = json.dumps(drv)
        db.add(ScoreHistory(customer_id=cust.id, churn_probability=round(prob, 4),
                            risk_tier=tier, scored_date=now))

    run = ScoringRun(
        timestamp=now,
        total_scored=len(customers),
        high_count=counts["High"],
        medium_count=counts["Medium"],
        low_count=counts["Low"],
        avg_probability=round(float(np.mean(probs)), 4),
        model_version=version,
    )
    db.add(run)
    db.commit()

    triggered = 0
    if trigger_interventions:
        from interventions import generate_interventions

        triggered = generate_interventions(db)

    summary = {
        "total_scored": len(customers),
        "high": counts["High"],
        "medium": counts["Medium"],
        "low": counts["Low"],
        "avg_probability": run.avg_probability,
        "model_version": version,
        "interventions_created": triggered,
        "timestamp": now.isoformat(),
    }
    print(f"[score] {summary}")
    return summary


if __name__ == "__main__":
    from db.database import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        score_all_customers(session)
    finally:
        session.close()
