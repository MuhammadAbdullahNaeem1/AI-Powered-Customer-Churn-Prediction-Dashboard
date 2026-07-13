"""Rule-based intervention engine.

Triggered after every scoring run. For each customer we decide the recommended
action from their risk tier, and create a *pending* intervention if there isn't
already an open (pending) one — so re-scoring daily doesn't spam duplicates.
"""
from __future__ import annotations

import json
from datetime import datetime


def recommend(tier: str, customer) -> dict | None:
    """Return the intervention recommendation for a risk tier, or None for Low."""
    if tier == "High":
        return {
            "intervention_type": "Immediate outreach + retention discount",
            "recommendation": (
                f"{customer.name} is at high risk of churning "
                f"({customer.churn_probability:.0%}). Flag for immediate personal "
                "outreach and offer a personalized retention discount "
                f"(their contract is '{customer.contract}')."
            ),
        }
    if tier == "Medium":
        return {
            "intervention_type": "Check-in call + feature highlight",
            "recommendation": (
                f"Schedule a proactive check-in call with {customer.name} "
                f"({customer.churn_probability:.0%} churn risk). Highlight unused "
                "features that fit their plan to reinforce value."
            ),
        }
    return None  # Low risk -> monitor only, no intervention record.


def top_driver_text(customer) -> str:
    """Human summary of the customer's leading churn driver, if precomputed."""
    if not customer.feature_contributions:
        return ""
    try:
        drivers = json.loads(customer.feature_contributions)
    except (ValueError, TypeError):
        return ""
    positive = [d for d in drivers if d.get("impact", 0) > 0]
    if not positive:
        return ""
    top = positive[0]
    return f" Leading factor: {top['label']} {top['direction']} their risk."


def generate_interventions(db) -> int:
    """Create pending interventions for High/Medium customers lacking an open one."""
    from db.models import Customer, Intervention

    created = 0
    open_by_customer = {
        row.customer_id
        for row in db.query(Intervention.customer_id)
        .filter(Intervention.status == "pending")
        .all()
    }

    high_medium = (
        db.query(Customer)
        .filter(Customer.risk_tier.in_(["High", "Medium"]))
        .all()
    )
    for cust in high_medium:
        if cust.id in open_by_customer:
            continue
        rec = recommend(cust.risk_tier, cust)
        if not rec:
            continue
        db.add(
            Intervention(
                customer_id=cust.id,
                intervention_type=rec["intervention_type"],
                recommendation=rec["recommendation"] + top_driver_text(cust),
                risk_tier=cust.risk_tier,
                churn_probability=cust.churn_probability,
                triggered_date=datetime.utcnow(),
                status="pending",
            )
        )
        created += 1

    db.commit()
    return created
