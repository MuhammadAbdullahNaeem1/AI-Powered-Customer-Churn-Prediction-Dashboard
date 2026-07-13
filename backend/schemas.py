"""Pydantic response models for the API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RiskCounts(BaseModel):
    high: int
    medium: int
    low: int


class DashboardSummary(BaseModel):
    total_customers: int
    high_risk: int
    medium_risk: int
    low_risk: int
    avg_churn_probability: float
    avg_prob_last_week: Optional[float] = None
    avg_prob_trend: Optional[float] = None  # signed delta vs last week
    high_risk_last_week: Optional[int] = None
    high_risk_trend: Optional[int] = None
    pending_interventions: int
    last_scored: Optional[datetime] = None
    model_version: Optional[str] = None


class CustomerRow(BaseModel):
    id: str
    name: str
    tenure: Optional[int] = None
    contract: Optional[str] = None
    monthly_charges: Optional[float] = None
    churn_probability: float
    risk_tier: str
    last_scored: Optional[datetime] = None


class CustomerList(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CustomerRow]


class FeatureContribution(BaseModel):
    feature: str
    label: str
    impact: float
    direction: str


class ScorePoint(BaseModel):
    scored_date: datetime
    churn_probability: float
    risk_tier: str


class InterventionOut(BaseModel):
    id: int
    customer_id: str
    customer_name: Optional[str] = None
    intervention_type: str
    recommendation: str
    risk_tier: str
    churn_probability: Optional[float] = None
    triggered_date: datetime
    status: str


class CustomerDetail(BaseModel):
    id: str
    name: str
    gender: Optional[str] = None
    senior_citizen: Optional[int] = None
    partner: Optional[str] = None
    dependents: Optional[str] = None
    tenure: Optional[int] = None
    phone_service: Optional[str] = None
    multiple_lines: Optional[str] = None
    internet_service: Optional[str] = None
    online_security: Optional[str] = None
    online_backup: Optional[str] = None
    device_protection: Optional[str] = None
    tech_support: Optional[str] = None
    streaming_tv: Optional[str] = None
    streaming_movies: Optional[str] = None
    contract: Optional[str] = None
    paperless_billing: Optional[str] = None
    payment_method: Optional[str] = None
    monthly_charges: Optional[float] = None
    total_charges: Optional[float] = None
    churn_probability: float
    risk_tier: str
    last_scored: Optional[datetime] = None
    feature_contributions: list[FeatureContribution] = []
    score_history: list[ScorePoint] = []
    interventions: list[InterventionOut] = []
    current_recommendation: Optional[dict] = None


class FeatureImportance(BaseModel):
    feature: str
    label: str
    importance: float


class ModelMetrics(BaseModel):
    model_version: Optional[str] = None
    training_date: Optional[datetime] = None
    roc_auc: Optional[float] = None
    f1: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    accuracy: Optional[float] = None
    n_train: Optional[int] = None
    n_test: Optional[int] = None
    feature_importances: list[FeatureImportance] = []


class InterventionStatusUpdate(BaseModel):
    status: str  # actioned / dismissed / pending


class TrendPoint(BaseModel):
    date: str
    avg_probability: float
    high: int
    medium: int
    low: int
