"""ORM models for the churn dashboard."""
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from db.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True)  # Telco customerID
    name = Column(String, nullable=False)

    # --- Raw feature columns from the Telco dataset ---
    gender = Column(String)
    senior_citizen = Column(Integer)
    partner = Column(String)
    dependents = Column(String)
    tenure = Column(Integer)
    phone_service = Column(String)
    multiple_lines = Column(String)
    internet_service = Column(String)
    online_security = Column(String)
    online_backup = Column(String)
    device_protection = Column(String)
    tech_support = Column(String)
    streaming_tv = Column(String)
    streaming_movies = Column(String)
    contract = Column(String)
    paperless_billing = Column(String)
    payment_method = Column(String)
    monthly_charges = Column(Float)
    total_charges = Column(Float)

    # Ground-truth label from the dataset (Yes/No) — kept for reference only.
    churn_label = Column(String)

    # --- Scoring outputs ---
    churn_probability = Column(Float, default=0.0)
    risk_tier = Column(String, default="Low", index=True)
    last_scored = Column(DateTime)
    # JSON string of top per-customer feature contributions (precomputed at scoring time)
    feature_contributions = Column(Text)

    interventions = relationship(
        "Intervention", back_populates="customer", cascade="all, delete-orphan"
    )
    score_history = relationship(
        "ScoreHistory", back_populates="customer", cascade="all, delete-orphan"
    )


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, ForeignKey("customers.id"), index=True)
    intervention_type = Column(String)  # e.g. "Immediate outreach + discount"
    recommendation = Column(Text)
    risk_tier = Column(String)
    churn_probability = Column(Float)
    triggered_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending", index=True)  # pending / actioned / dismissed

    customer = relationship("Customer", back_populates="interventions")


class ScoreHistory(Base):
    __tablename__ = "score_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, ForeignKey("customers.id"), index=True)
    churn_probability = Column(Float)
    risk_tier = Column(String)
    scored_date = Column(DateTime, default=datetime.utcnow, index=True)

    customer = relationship("Customer", back_populates="score_history")


class ScoringRun(Base):
    __tablename__ = "scoring_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_scored = Column(Integer)
    high_count = Column(Integer)
    medium_count = Column(Integer)
    low_count = Column(Integer)
    avg_probability = Column(Float)
    model_version = Column(String)


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_version = Column(String)
    training_date = Column(DateTime, default=datetime.utcnow)
    roc_auc = Column(Float)
    f1 = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    accuracy = Column(Float)
    feature_importances = Column(Text)  # JSON: [{"feature": str, "importance": float}, ...]
    n_train = Column(Integer)
    n_test = Column(Integer)
