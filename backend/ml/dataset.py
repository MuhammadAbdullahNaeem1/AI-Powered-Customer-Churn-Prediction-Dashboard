"""Dataset acquisition: download the IBM Telco churn dataset from Kaggle,
falling back to a realistic synthetic dataset with the same schema if the
Kaggle API is unavailable (no credentials / offline)."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import DATA_DIR, RAW_CSV  # noqa: E402

KAGGLE_DATASET = "blastchar/telco-customer-churn"
TELCO_CSV_NAME = "WA_Fn-UseC_-Telco-Customer-Churn.csv"


def _download_from_kaggle() -> bool:
    """Attempt to download + unzip the Telco dataset via the Kaggle API."""
    try:
        # KaggleApi reads KAGGLE_USERNAME/KAGGLE_KEY from the environment (.env).
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        api.dataset_download_files(KAGGLE_DATASET, path=str(DATA_DIR), quiet=False)
        zip_path = DATA_DIR / "telco-customer-churn.zip"
        if zip_path.exists():
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(DATA_DIR)
            zip_path.unlink(missing_ok=True)
        src = DATA_DIR / TELCO_CSV_NAME
        if src.exists():
            src.rename(RAW_CSV)
            return True
    except Exception as exc:  # noqa: BLE001
        print(f"[dataset] Kaggle download unavailable ({exc}). Using synthetic fallback.")
    return False


def _synthesize(n: int = 7043, seed: int = 42) -> pd.DataFrame:
    """Generate a synthetic dataset that mirrors the IBM Telco schema and its
    known churn relationships (month-to-month + high charges + low tenure churn more)."""
    rng = np.random.default_rng(seed)

    def pick(options, p=None):
        return rng.choice(options, size=n, p=p)

    gender = pick(["Male", "Female"])
    senior = rng.binomial(1, 0.16, n)
    partner = pick(["Yes", "No"], [0.48, 0.52])
    dependents = pick(["Yes", "No"], [0.30, 0.70])
    tenure = rng.integers(0, 73, n)
    phone = pick(["Yes", "No"], [0.90, 0.10])
    multiple = np.where(
        phone == "No", "No phone service", pick(["Yes", "No"], [0.42, 0.58])
    )
    internet = pick(["DSL", "Fiber optic", "No"], [0.34, 0.44, 0.22])

    def addon():
        return np.where(
            internet == "No",
            "No internet service",
            pick(["Yes", "No"], [0.5, 0.5]),
        )

    online_security = addon()
    online_backup = addon()
    device_protection = addon()
    tech_support = addon()
    streaming_tv = addon()
    streaming_movies = addon()
    contract = pick(["Month-to-month", "One year", "Two year"], [0.55, 0.21, 0.24])
    paperless = pick(["Yes", "No"], [0.59, 0.41])
    payment = pick(
        [
            "Electronic check",
            "Mailed check",
            "Bank transfer (automatic)",
            "Credit card (automatic)",
        ],
        [0.34, 0.23, 0.22, 0.21],
    )
    monthly = np.round(rng.uniform(18.25, 118.75, n), 2)
    # Fiber optic customers pay more.
    monthly = np.where(internet == "Fiber optic", monthly * 1.15, monthly).round(2)
    total = np.round(monthly * np.maximum(tenure, 1) * rng.uniform(0.9, 1.05, n), 2)
    total = np.where(tenure == 0, 0.0, total)

    # Churn propensity driven by realistic factors.
    logit = (
        -1.8
        + (contract == "Month-to-month") * 1.7
        + (contract == "Two year") * -1.4
        + (internet == "Fiber optic") * 0.9
        + (payment == "Electronic check") * 0.7
        + (tech_support == "No") * 0.4
        + (online_security == "No") * 0.4
        + senior * 0.4
        + (monthly - 65) / 40.0
        - (tenure - 32) / 24.0
    )
    prob = 1 / (1 + np.exp(-logit))
    churn = np.where(rng.random(n) < prob, "Yes", "No")

    customer_ids = [f"{rng.integers(1000, 9999)}-{_rand_tag(rng)}" for _ in range(n)]

    return pd.DataFrame(
        {
            "customerID": customer_ids,
            "gender": gender,
            "SeniorCitizen": senior,
            "Partner": partner,
            "Dependents": dependents,
            "tenure": tenure,
            "PhoneService": phone,
            "MultipleLines": multiple,
            "InternetService": internet,
            "OnlineSecurity": online_security,
            "OnlineBackup": online_backup,
            "DeviceProtection": device_protection,
            "TechSupport": tech_support,
            "StreamingTV": streaming_tv,
            "StreamingMovies": streaming_movies,
            "Contract": contract,
            "PaperlessBilling": paperless,
            "PaymentMethod": payment,
            "MonthlyCharges": monthly,
            "TotalCharges": total,
            "Churn": churn,
        }
    )


def _rand_tag(rng) -> str:
    letters = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    return "".join(rng.choice(letters, size=5))


def load_dataset(force_download: bool = False) -> pd.DataFrame:
    """Return the raw Telco dataframe, acquiring it if necessary.

    Order of preference: existing cached CSV -> Kaggle download -> synthetic.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_CSV.exists() and not force_download:
        return pd.read_csv(RAW_CSV)

    if _download_from_kaggle() and RAW_CSV.exists():
        print(f"[dataset] Downloaded Telco dataset from Kaggle -> {RAW_CSV}")
        return pd.read_csv(RAW_CSV)

    print("[dataset] Generating synthetic Telco-schema dataset (7043 rows).")
    df = _synthesize()
    df.to_csv(RAW_CSV, index=False)
    return df


if __name__ == "__main__":
    frame = load_dataset(force_download="--download" in sys.argv)
    print(frame.shape)
    print(frame["Churn"].value_counts())
