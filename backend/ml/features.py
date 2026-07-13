"""Shared feature definitions and preprocessing used by both training and scoring.

We keep the raw IBM Telco column names here as the single source of truth, and
provide a mapping to/from the snake_case columns stored on the Customer ORM model.
"""
from __future__ import annotations

import pandas as pd

TARGET = "Churn"
ID_COL = "customerID"

# Numeric features (scaled) and categorical features (one-hot encoded).
NUMERIC_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges", "SeniorCitizen"]
CATEGORICAL_FEATURES = [
    "gender",
    "Partner",
    "Dependents",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Map raw Telco column -> Customer ORM attribute (snake_case).
RAW_TO_ORM = {
    "customerID": "id",
    "gender": "gender",
    "SeniorCitizen": "senior_citizen",
    "Partner": "partner",
    "Dependents": "dependents",
    "tenure": "tenure",
    "PhoneService": "phone_service",
    "MultipleLines": "multiple_lines",
    "InternetService": "internet_service",
    "OnlineSecurity": "online_security",
    "OnlineBackup": "online_backup",
    "DeviceProtection": "device_protection",
    "TechSupport": "tech_support",
    "StreamingTV": "streaming_tv",
    "StreamingMovies": "streaming_movies",
    "Contract": "contract",
    "PaperlessBilling": "paperless_billing",
    "PaymentMethod": "payment_method",
    "MonthlyCharges": "monthly_charges",
    "TotalCharges": "total_charges",
}
ORM_TO_RAW = {v: k for k, v in RAW_TO_ORM.items()}

# Human-friendly labels for the dashboard feature-importance chart.
FRIENDLY_LABELS = {
    "tenure": "Tenure (months)",
    "MonthlyCharges": "Monthly charges",
    "TotalCharges": "Total charges",
    "SeniorCitizen": "Senior citizen",
    "Contract": "Contract type",
    "InternetService": "Internet service",
    "PaymentMethod": "Payment method",
    "OnlineSecurity": "Online security",
    "TechSupport": "Tech support",
    "PaperlessBilling": "Paperless billing",
    "OnlineBackup": "Online backup",
    "DeviceProtection": "Device protection",
    "StreamingTV": "Streaming TV",
    "StreamingMovies": "Streaming movies",
    "MultipleLines": "Multiple lines",
    "PhoneService": "Phone service",
    "Partner": "Has partner",
    "Dependents": "Has dependents",
    "gender": "Gender",
}


def clean_raw_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean a raw Telco dataframe: coerce TotalCharges, fill blanks."""
    df = df.copy()
    # TotalCharges has blank strings for brand-new (tenure 0) customers.
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df["TotalCharges"] = df["TotalCharges"].fillna(0.0)
    df["tenure"] = pd.to_numeric(df["tenure"], errors="coerce").fillna(0).astype(int)
    df["MonthlyCharges"] = pd.to_numeric(df["MonthlyCharges"], errors="coerce").fillna(0.0)
    df["SeniorCitizen"] = pd.to_numeric(df["SeniorCitizen"], errors="coerce").fillna(0).astype(int)
    # Fill any missing categoricals with a sentinel so the encoder stays stable.
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)
    return df


def customers_to_feature_frame(customers) -> pd.DataFrame:
    """Build a raw-schema feature DataFrame from a list of Customer ORM rows."""
    rows = []
    for c in customers:
        rows.append(
            {
                "customerID": c.id,
                "gender": c.gender,
                "SeniorCitizen": c.senior_citizen,
                "Partner": c.partner,
                "Dependents": c.dependents,
                "tenure": c.tenure,
                "PhoneService": c.phone_service,
                "MultipleLines": c.multiple_lines,
                "InternetService": c.internet_service,
                "OnlineSecurity": c.online_security,
                "OnlineBackup": c.online_backup,
                "DeviceProtection": c.device_protection,
                "TechSupport": c.tech_support,
                "StreamingTV": c.streaming_tv,
                "StreamingMovies": c.streaming_movies,
                "Contract": c.contract,
                "PaperlessBilling": c.paperless_billing,
                "PaymentMethod": c.payment_method,
                "MonthlyCharges": c.monthly_charges,
                "TotalCharges": c.total_charges,
            }
        )
    df = pd.DataFrame(rows)
    return clean_raw_dataframe(df)
