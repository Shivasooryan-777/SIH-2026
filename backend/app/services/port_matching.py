"""
Module B — Port-Matching Engine
================================
Implements dynamic vessel-to-port physical compatibility verification and ranking
per docs/blueprint.md Module B:
1. Exact compatibility rule:
   is_compatible(vessel, port, date) =
       (vessel.required_draft_m <= effective_draft(port, date))
       AND (vessel.typical_loa_m <= port.max_loa_m)
       AND (vessel.typical_beam_m <= port.max_beam_m)

2. Dynamic effective draft computation:
   effective_draft(port, date) =
       PortDraftAdvisory.available_draft_m for that port/date if present in database,
       ELSE port.baseline_draft_m * seasonal_factor(port, date)

NON-HARDCODED INVARIANT:
Port draft is NEVER a fixed constant in the codebase. It always queries PortDraftAdvisory
dynamically for real-time/manual overrides, falling back to port.baseline_draft_m with
the documented seasonal siltation adjustment.

SEASONAL MONSOON-SILTATION APPROXIMATION (DISCLOSED LIMITATION):
Documented reasoned engineering approximations reflecting published port advisory trends
and seasonal riverine siltation on the East Coast of India, not live bathymetric surveying
or real-time tidal gauge feeds:
- Southwest Monsoon (June 1 – September 30): 0.90 factor (10% draft reduction)
- Post-Monsoon / Cyclonic Season (October 1 – November 30): 0.95 factor (5% draft reduction)
- Fair Weather Season (December 1 – May 31): 1.00 factor (full baseline draft)
- Origin loading ports (outside India): 1.00 factor unless advisory is on record.

RANKING LOGIC:
Compatible vessel types are ranked largest-safe-first (Capesize > Panamax > Supramax > Handysize)
because larger deadweight classes minimize per-metric-ton transport costs.
"""

from datetime import date as DateType
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models import Port, PortDraftAdvisory, VesselType


# Documented Seasonal Siltation Factors (East Coast of India Ports)
SEASONAL_FACTORS: Dict[str, float] = {
    "southwest_monsoon": 0.90,  # Jun 1 – Sep 30
    "post_monsoon_cyclone": 0.95,  # Oct 1 – Nov 30
    "fair_weather": 1.00,  # Dec 1 – May 31
}


def get_seasonal_draft_factor(port: Port, eval_date: DateType) -> Decimal:
    """
    Compute documented seasonal draft multiplier for East Coast Indian destination ports.
    Origin loading ports outside India use 1.00 unless explicitly overridden via advisory.
    """
    if port.port_role != "destination" or port.country.lower() != "india":
        return Decimal("1.00")

    month = eval_date.month
    if 6 <= month <= 9:
        factor = SEASONAL_FACTORS["southwest_monsoon"]
    elif 10 <= month <= 11:
        factor = SEASONAL_FACTORS["post_monsoon_cyclone"]
    else:
        factor = SEASONAL_FACTORS["fair_weather"]

    return Decimal(str(factor))


def effective_draft(port: Port, eval_date: DateType, db: Session) -> Decimal:
    """
    Calculate effective draft for a given port and date.
    1. Checks PortDraftAdvisory for date-specific override.
    2. Falls back to port.baseline_draft_m multiplied by seasonal factor.
    NEVER uses a hardcoded draft literal.
    """
    # 1. Dynamic override check from PortDraftAdvisory
    advisory = (
        db.query(PortDraftAdvisory)
        .filter(PortDraftAdvisory.port_id == port.port_id, PortDraftAdvisory.date == eval_date)
        .first()
    )

    if advisory is not None and advisory.available_draft_m is not None:
        return Decimal(str(advisory.available_draft_m))

    # 2. Baseline draft with documented seasonal adjustment
    factor = get_seasonal_draft_factor(port, eval_date)
    adjusted = Decimal(str(port.baseline_draft_m)) * factor
    return Decimal(str(round(adjusted, 2)))


def is_compatible(vessel: VesselType, port: Port, eval_date: DateType, db: Session) -> bool:
    """
    Exact compatibility rule from docs/blueprint.md Module B:
    (vessel.required_draft_m <= effective_draft(port, date))
    AND (vessel.typical_loa_m <= port.max_loa_m)
    AND (vessel.typical_beam_m <= port.max_beam_m)
    """
    eff_draft = effective_draft(port, eval_date, db)

    draft_ok = Decimal(str(vessel.required_draft_m)) <= eff_draft
    loa_ok = Decimal(str(vessel.typical_loa_m)) <= Decimal(str(port.max_loa_m))
    beam_ok = Decimal(str(vessel.typical_beam_m)) <= Decimal(str(port.max_beam_m))

    return draft_ok and loa_ok and beam_ok


def evaluate_port_compatibility(
    port: Port,
    eval_date: DateType,
    db: Session,
    cargo_volume_tons: Optional[int] = None,
) -> Dict:
    """
    Evaluate all registered vessel types against a port on a specific date.
    Returns ranked compatible vessels (largest-safe-first) and detailed constraint margins.
    """
    eff_draft = effective_draft(port, eval_date, db)
    all_vessels: List[VesselType] = (
        db.query(VesselType)
        .order_by(VesselType.max_dwt.desc())  # Largest DWT first
        .all()
    )

    compatible_vessels = []
    incompatible_vessels = []

    for v in all_vessels:
        v_draft = Decimal(str(v.required_draft_m))
        v_loa = Decimal(str(v.typical_loa_m))
        v_beam = Decimal(str(v.typical_beam_m))

        draft_margin = eff_draft - v_draft
        loa_margin = Decimal(str(port.max_loa_m)) - v_loa
        beam_margin = Decimal(str(port.max_beam_m)) - v_beam

        compatible = (draft_margin >= 0) and (loa_margin >= 0) and (beam_margin >= 0)

        # Capacity check if cargo volume provided
        capacity_status = "sufficient"
        if cargo_volume_tons is not None:
            if cargo_volume_tons > v.max_dwt:
                capacity_status = f"exceeds_max_dwt_{v.max_dwt}"
            elif cargo_volume_tons < v.min_dwt:
                capacity_status = f"below_min_dwt_{v.min_dwt}"

        v_summary = {
            "vessel_type_id": v.vessel_type_id,
            "name": v.name,
            "min_dwt": v.min_dwt,
            "max_dwt": v.max_dwt,
            "required_draft_m": float(v_draft),
            "typical_loa_m": float(v_loa),
            "typical_beam_m": float(v_beam),
            "is_compatible": compatible,
            "draft_margin_m": float(draft_margin),
            "loa_margin_m": float(loa_margin),
            "beam_margin_m": float(beam_margin),
            "cargo_capacity_status": capacity_status,
        }

        if compatible:
            compatible_vessels.append(v_summary)
        else:
            incompatible_vessels.append(v_summary)

    return {
        "port_id": port.port_id,
        "port_name": port.name,
        "port_role": port.port_role,
        "country": port.country,
        "date": eval_date.isoformat(),
        "baseline_draft_m": float(Decimal(str(port.baseline_draft_m))),
        "effective_draft_m": float(eff_draft),
        "seasonal_factor": float(get_seasonal_draft_factor(port, eval_date)),
        "ranked_compatible_vessels": compatible_vessels,  # Largest-safe-first
        "incompatible_vessels": incompatible_vessels,
    }
