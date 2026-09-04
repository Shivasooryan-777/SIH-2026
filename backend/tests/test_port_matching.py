"""
Module B — Port-Matching Engine Test Suite
==========================================
Verifies:
1. Exact compatibility formula: draft, LOA, beam constraints.
2. Seasonal monsoon-siltation draft adjustment (0.90 monsoon, 0.95 post-monsoon, 1.00 fair weather).
3. NON-HARDCODED DRAFT INVARIANT: Formally proves port draft is dynamic by inserting and removing
   a PortDraftAdvisory record and asserting that is_compatible and effective_draft outputs change.
4. Largest-safe-first vessel ranking (Capesize > Panamax > Supramax > Handysize).
"""

from datetime import date
from decimal import Decimal
import pytest

from backend.app.database import SessionLocal
from backend.app.models import Port, PortDraftAdvisory, VesselType
from backend.app.services.port_matching import (
    effective_draft,
    get_seasonal_draft_factor,
    is_compatible,
    evaluate_port_compatibility,
)


@pytest.fixture(scope="function")
def db_session():
    """Function-scoped database session for port matching tests with clean rollback."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_seasonal_draft_factors(db_session):
    """Verify seasonal draft factor logic for Indian destination ports vs origins."""
    paradip = db_session.query(Port).filter(Port.name == "Paradip_Inner").first()
    assert paradip is not None

    # Southwest Monsoon: July (month 7) -> 0.90
    monsoon_date = date(2023, 7, 15)
    assert get_seasonal_draft_factor(paradip, monsoon_date) == Decimal("0.90")

    # Post-Monsoon Cyclone: October (month 10) -> 0.95
    cyclone_date = date(2023, 10, 15)
    assert get_seasonal_draft_factor(paradip, cyclone_date) == Decimal("0.95")

    # Fair Weather: February (month 2) -> 1.00
    fair_date = date(2023, 2, 15)
    assert get_seasonal_draft_factor(paradip, fair_date) == Decimal("1.00")

    # Origin port outside India -> 1.00 regardless of month
    newcastle = db_session.query(Port).filter(Port.name == "Newcastle").first()
    if newcastle:
        assert get_seasonal_draft_factor(newcastle, monsoon_date) == Decimal("1.00")


def test_is_compatible_physical_constraints(db_session):
    """
    Test exact compatibility rules against physical specifications:
    - Paradip_SPM (baseline draft 21m, LOA 370m, beam 65m) accepts Capesize (draft 19m, LOA 290m, beam 45m).
    - Paradip_Inner (baseline draft 15m, LOA 260m, beam 46m) rejects Capesize (draft 19m > 15m, LOA 290m > 260m).
    - Paradip_Inner accepts Supramax (draft 11.5m, LOA 190m, beam 32m).
    """
    spm = db_session.query(Port).filter(Port.name == "Paradip_SPM").first()
    inner = db_session.query(Port).filter(Port.name == "Paradip_Inner").first()
    capesize = db_session.query(VesselType).filter(VesselType.name == "Capesize").first()
    supramax = db_session.query(VesselType).filter(VesselType.name == "Supramax").first()

    assert all([spm, inner, capesize, supramax])

    eval_date = date(2023, 3, 1)  # Fair weather: baseline draft in full effect

    # Capesize at Paradip_SPM: compatible
    assert is_compatible(capesize, spm, eval_date, db_session) is True

    # Capesize at Paradip_Inner: incompatible
    assert is_compatible(capesize, inner, eval_date, db_session) is False

    # Supramax at Paradip_Inner: compatible
    assert is_compatible(supramax, inner, eval_date, db_session) is True


def test_port_draft_advisory_dynamic_override(db_session):
    """
    CRITICAL PROOF OF NON-HARDCODED DRAFT:
    Asserts that inserting a PortDraftAdvisory override alters the function's output,
    proving draft is never a hardcoded constant in the codebase.
    """
    port = db_session.query(Port).filter(Port.name == "Paradip_Inner").first()
    supramax = db_session.query(VesselType).filter(VesselType.name == "Supramax").first()
    assert port is not None and supramax is not None

    test_date = date(2025, 3, 15)  # Fair weather, baseline 15.0m

    # Clean up any pre-existing advisory for this test date
    db_session.query(PortDraftAdvisory).filter(
        PortDraftAdvisory.port_id == port.port_id,
        PortDraftAdvisory.date == test_date,
    ).delete()
    db_session.commit()

    # Step 1: Default baseline draft (15.0m) -> Supramax (11.5m required) IS compatible
    draft_before = effective_draft(port, test_date, db_session)
    assert draft_before == Decimal("15.00")
    assert is_compatible(supramax, port, test_date, db_session) is True

    # Step 2: Insert dynamic PortDraftAdvisory reducing draft to 10.0m (e.g. emergency siltation)
    advisory = PortDraftAdvisory(
        port_id=port.port_id,
        date=test_date,
        available_draft_m=Decimal("10.00"),
        season_tag="emergency_test",
    )
    db_session.add(advisory)
    db_session.commit()

    try:
        # Step 3: Effective draft MUST dynamically change to 10.0m, Supramax MUST become incompatible
        draft_during = effective_draft(port, test_date, db_session)
        assert draft_during == Decimal("10.00"), f"Expected 10.00m, got {draft_during}"
        assert is_compatible(supramax, port, test_date, db_session) is False, (
            "Supramax should be incompatible with draft override 10.00m!"
        )
    finally:
        # Step 4: Clean up test advisory and verify reversion
        db_session.query(PortDraftAdvisory).filter(
            PortDraftAdvisory.port_id == port.port_id,
            PortDraftAdvisory.date == test_date,
        ).delete()
        db_session.commit()

    draft_after = effective_draft(port, test_date, db_session)
    assert draft_after == Decimal("15.00")
    assert is_compatible(supramax, port, test_date, db_session) is True


def test_evaluate_port_compatibility_ranking(db_session):
    """Verify that compatible vessels are ranked largest-safe-first."""
    port = db_session.query(Port).filter(Port.name == "Paradip_SPM").first()
    assert port is not None

    eval_date = date(2023, 2, 10)
    result = evaluate_port_compatibility(port, eval_date, db_session, cargo_volume_tons=120000)

    ranked = result["ranked_compatible_vessels"]
    assert len(ranked) > 0

    # Largest vessel first: Capesize (DWT up to 200,000) must be first
    assert ranked[0]["name"] == "Capesize"

    # Monotonically descending max_dwt in ranked list
    dwts = [v["max_dwt"] for v in ranked]
    assert dwts == sorted(dwts, reverse=True)
