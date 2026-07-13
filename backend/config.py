"""Central configuration loaded from environment / .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/ directory
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./churn.db")
MODEL_PATH = str(BASE_DIR / os.getenv("MODEL_PATH", "ml/model.pkl"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

# Raw dataset location (downloaded from Kaggle or synthesized as a fallback)
DATA_DIR = PROJECT_ROOT / "data"
RAW_CSV = DATA_DIR / "telco_churn.csv"

# Risk tier thresholds (probability of churn)
RISK_LOW_MAX = 0.30
RISK_MEDIUM_MAX = 0.60


def risk_tier(prob: float) -> str:
    """Map a churn probability to a Low / Medium / High risk tier."""
    if prob < RISK_LOW_MAX:
        return "Low"
    if prob < RISK_MEDIUM_MAX:
        return "Medium"
    return "High"
