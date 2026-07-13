"""Train an XGBoost churn classifier on the IBM Telco dataset.

Builds a single sklearn Pipeline (preprocessing + model) so scoring never has to
re-derive encoders. Persists the pipeline to model.pkl via joblib and records
metrics + feature importances in the model_metadata table.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import MODEL_PATH  # noqa: E402
from ml.dataset import load_dataset  # noqa: E402
from ml.features import (  # noqa: E402
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    FRIENDLY_LABELS,
    NUMERIC_FEATURES,
    TARGET,
    clean_raw_dataframe,
)


def _build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def _aggregate_importances(pipeline: Pipeline) -> list[dict]:
    """Sum XGBoost gains of one-hot columns back to their source feature."""
    ohe: OneHotEncoder = pipeline.named_steps["preprocess"].named_transformers_["cat"]
    cat_names = list(ohe.get_feature_names_out(CATEGORICAL_FEATURES))
    feature_names = NUMERIC_FEATURES + cat_names

    importances = pipeline.named_steps["model"].feature_importances_
    grouped: dict[str, float] = defaultdict(float)
    for name, imp in zip(feature_names, importances):
        # Numeric names map directly; one-hot names look like "Contract_Two year".
        if name in NUMERIC_FEATURES:
            source = name
        else:
            source = name.rsplit("_", 1)[0] if "_" in name else name
            # Recover the original categorical column (handle values containing "_").
            source = next(
                (c for c in CATEGORICAL_FEATURES if name.startswith(c + "_")), source
            )
        grouped[source] += float(imp)

    total = sum(grouped.values()) or 1.0
    ranked = sorted(grouped.items(), key=lambda kv: kv[1], reverse=True)
    return [
        {
            "feature": src,
            "label": FRIENDLY_LABELS.get(src, src),
            "importance": round(val / total, 4),
        }
        for src, val in ranked
    ]


def train_model(persist_metadata: bool = True) -> dict:
    df = load_dataset()
    df = clean_raw_dataframe(df)
    df = df[df[TARGET].isin(["Yes", "No"])].copy()

    X = df[FEATURE_COLUMNS]
    y = (df[TARGET] == "Yes").astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = _build_pipeline()
    pipeline.fit(X_train, y_train)

    proba = pipeline.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)

    metrics = {
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        "f1": round(float(f1_score(y_test, preds)), 4),
        "precision": round(float(precision_score(y_test, preds)), 4),
        "recall": round(float(recall_score(y_test, preds)), 4),
        "accuracy": round(float(accuracy_score(y_test, preds)), 4),
    }
    importances = _aggregate_importances(pipeline)
    version = datetime.utcnow().strftime("v%Y.%m.%d.%H%M")

    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "version": version,
            "feature_columns": FEATURE_COLUMNS,
            "trained_at": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "importances": importances,
            "n_train": len(X_train),
            "n_test": len(X_test),
        },
        MODEL_PATH,
    )

    print(f"[train] Model {version} saved -> {MODEL_PATH}")
    print(f"[train] Metrics: {metrics}")
    print("[train] Top features:", [i["feature"] for i in importances[:5]])

    if persist_metadata:
        _persist_metadata(version, metrics, importances, len(X_train), len(X_test))

    return {"version": version, "metrics": metrics, "importances": importances}


def _persist_metadata(version, metrics, importances, n_train, n_test):
    from db.database import SessionLocal, init_db
    from db.models import ModelMetadata

    init_db()
    db = SessionLocal()
    try:
        db.add(
            ModelMetadata(
                model_version=version,
                training_date=datetime.utcnow(),
                roc_auc=metrics["roc_auc"],
                f1=metrics["f1"],
                precision=metrics["precision"],
                recall=metrics["recall"],
                accuracy=metrics["accuracy"],
                feature_importances=json.dumps(importances),
                n_train=n_train,
                n_test=n_test,
            )
        )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    train_model()
