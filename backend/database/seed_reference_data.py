"""
Reference Data Seeding Pipeline
===============================
Seeds reference and master data into Neon Postgres:
1. Ports (14 rows: 7 destination, 7 origin)
2. VesselTypes (4 rows: Handysize, Supramax, Panamax, Capesize)
3. Routes (8 rows with FK resolution to Ports)
4. RiskEvents (4 rows with FK resolution to Routes)

Strictly validates:
- Schema column alignment
- Non-null constraints
- Foreign key references
- Natural-key idempotency (safe to run repeatedly without creating duplicates)

SECURITY NOTICE:
Never prints or logs database credentials or connection strings.
"""

import csv
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.database import SessionLocal
from backend.app.models import Port, VesselType, Route, RiskEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("seed_reference_data")

RAW_DATA_DIR = REPO_ROOT / "data" / "raw"
PORTS_CSV = RAW_DATA_DIR / "ports.csv"
VESSEL_TYPES_CSV = RAW_DATA_DIR / "vessel_types.csv"
ROUTES_CSV = RAW_DATA_DIR / "routes.csv"
RISK_EVENTS_CSV = RAW_DATA_DIR / "risk_events.csv"


def get_entity_id(entity: Any, id_field: str) -> int:
    """Safely extract integer primary key from ORM entity to satisfy static type checkers."""
    return int(getattr(entity, id_field))


def verify_raw_files_exist() -> None:
    """Ensure all four required raw CSV files are present."""
    missing = []
    for f in [PORTS_CSV, VESSEL_TYPES_CSV, ROUTES_CSV, RISK_EVENTS_CSV]:
        if not f.exists():
            missing.append(str(f.relative_to(REPO_ROOT)))
    if missing:
        raise FileNotFoundError(f"Missing required raw CSV files: {missing}. Aborting.")
    logger.info("All four required raw reference CSV files verified in data/raw/.")


def seed_ports(db) -> Dict[str, int]:
    """
    Load data/raw/ports.csv and insert into 'ports' table.
    Natural key: 'name'.
    Returns mapping: port_name -> port_id.
    """
    logger.info("--- Seeding Ports ---")
    expected_headers = [
        "name", "country", "port_role", "max_loa_m",
        "max_beam_m", "baseline_draft_m", "latitude", "longitude"
    ]

    port_map: Dict[str, int] = {}
    inserted_count = 0
    existing_count = 0

    with open(PORTS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected_headers:
            raise ValueError(
                f"ports.csv header mismatch. Expected {expected_headers}, got {reader.fieldnames}"
            )

        for row_idx, row in enumerate(reader, start=1):
            name = row["name"].strip()
            country = row["country"].strip()
            port_role = row["port_role"].strip()
            max_loa_m_str = row["max_loa_m"].strip()
            max_beam_m_str = row["max_beam_m"].strip()
            baseline_draft_m_str = row["baseline_draft_m"].strip()
            lat_str = row["latitude"].strip() if row.get("latitude") else None
            lon_str = row["longitude"].strip() if row.get("longitude") else None

            # Non-null validation
            if not all([name, country, port_role, max_loa_m_str, max_beam_m_str, baseline_draft_m_str]):
                raise ValueError(f"ports.csv row {row_idx} contains empty required field: {row}")

            if port_role not in {"origin", "destination"}:
                raise ValueError(f"ports.csv row {row_idx} has invalid port_role '{port_role}'")

            # Check if port already exists by natural key
            existing = db.query(Port).filter(Port.name == name).first()
            if existing:
                port_map[name] = get_entity_id(existing, "port_id")
                existing_count += 1
            else:
                new_port = Port(
                    name=name,
                    country=country,
                    port_role=port_role,
                    max_loa_m=Decimal(max_loa_m_str),
                    max_beam_m=Decimal(max_beam_m_str),
                    baseline_draft_m=Decimal(baseline_draft_m_str),
                    latitude=Decimal(lat_str) if lat_str else None,
                    longitude=Decimal(lon_str) if lon_str else None,
                )
                db.add(new_port)
                db.flush()  # populate port_id
                port_map[name] = get_entity_id(new_port, "port_id")
                inserted_count += 1

    db.commit()
    logger.info("Ports seed complete: %d inserted, %d existing (total tracked: %d)", inserted_count, existing_count, len(port_map))
    return port_map


def seed_vessel_types(db) -> Dict[str, int]:
    """
    Load data/raw/vessel_types.csv and insert into 'vessel_types' table.
    Natural key: 'name'.
    Returns mapping: vessel_type_name -> vessel_type_id.
    """
    logger.info("--- Seeding Vessel Types ---")
    expected_headers = [
        "name", "min_dwt", "max_dwt", "required_draft_m",
        "typical_loa_m", "typical_beam_m", "standard_speed_knots", "fuel_curve_coef"
    ]

    vessel_map: Dict[str, int] = {}
    inserted_count = 0
    existing_count = 0

    with open(VESSEL_TYPES_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected_headers:
            raise ValueError(
                f"vessel_types.csv header mismatch. Expected {expected_headers}, got {reader.fieldnames}"
            )

        for row_idx, row in enumerate(reader, start=1):
            name = row["name"].strip()
            min_dwt_str = row["min_dwt"].strip()
            max_dwt_str = row["max_dwt"].strip()
            required_draft_m_str = row["required_draft_m"].strip()
            typical_loa_m_str = row["typical_loa_m"].strip()
            typical_beam_m_str = row["typical_beam_m"].strip()
            std_speed_str = row["standard_speed_knots"].strip()
            fuel_coef_str = row["fuel_curve_coef"].strip()

            # Non-null validation
            if not all([name, min_dwt_str, max_dwt_str, required_draft_m_str,
                        typical_loa_m_str, typical_beam_m_str, std_speed_str, fuel_coef_str]):
                raise ValueError(f"vessel_types.csv row {row_idx} contains empty required field: {row}")

            existing = db.query(VesselType).filter(VesselType.name == name).first()
            if existing:
                vessel_map[name] = get_entity_id(existing, "vessel_type_id")
                existing_count += 1
            else:
                new_vessel = VesselType(
                    name=name,
                    min_dwt=int(min_dwt_str),
                    max_dwt=int(max_dwt_str),
                    required_draft_m=Decimal(required_draft_m_str),
                    typical_loa_m=Decimal(typical_loa_m_str),
                    typical_beam_m=Decimal(typical_beam_m_str),
                    standard_speed_knots=Decimal(std_speed_str),
                    fuel_curve_coef=Decimal(fuel_coef_str),
                )
                db.add(new_vessel)
                db.flush()
                vessel_map[name] = get_entity_id(new_vessel, "vessel_type_id")
                inserted_count += 1

    db.commit()
    logger.info("VesselTypes seed complete: %d inserted, %d existing (total tracked: %d)", inserted_count, existing_count, len(vessel_map))
    return vessel_map


def seed_routes(db, port_map: Dict[str, int]) -> Dict[Tuple[str, str], int]:
    """
    Load data/raw/routes.csv and insert into 'routes' table.
    Resolves origin_port_id (name) and destination_port_id (name) to foreign keys.
    Natural key: (origin_port_id, destination_port_id).
    Returns mapping: (origin_name, destination_name) -> route_id.
    """
    logger.info("--- Seeding Routes ---")
    expected_headers = ["origin_port_id", "destination_port_id", "distance_nm", "typical_transit_days"]

    route_map: Dict[Tuple[str, str], int] = {}
    inserted_count = 0
    existing_count = 0

    with open(ROUTES_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected_headers:
            raise ValueError(
                f"routes.csv header mismatch. Expected {expected_headers}, got {reader.fieldnames}"
            )

        for row_idx, row in enumerate(reader, start=1):
            origin_name = row["origin_port_id"].strip()
            dest_name = row["destination_port_id"].strip()
            dist_str = row["distance_nm"].strip()
            transit_str = row["typical_transit_days"].strip()

            if not all([origin_name, dest_name, dist_str, transit_str]):
                raise ValueError(f"routes.csv row {row_idx} contains empty required field: {row}")

            # Foreign key resolution
            if origin_name not in port_map:
                raise ValueError(
                    f"routes.csv row {row_idx}: origin port '{origin_name}' not found in Ports data!"
                )
            if dest_name not in port_map:
                raise ValueError(
                    f"routes.csv row {row_idx}: destination port '{dest_name}' not found in Ports data!"
                )

            origin_id = port_map[origin_name]
            dest_id = port_map[dest_name]

            existing = db.query(Route).filter(
                Route.origin_port_id == origin_id,
                Route.destination_port_id == dest_id,
            ).first()

            if existing:
                route_map[(origin_name, dest_name)] = get_entity_id(existing, "route_id")
                existing_count += 1
            else:
                new_route = Route(
                    origin_port_id=origin_id,
                    destination_port_id=dest_id,
                    distance_nm=int(dist_str),
                    typical_transit_days=Decimal(transit_str),
                )
                db.add(new_route)
                db.flush()
                route_map[(origin_name, dest_name)] = get_entity_id(new_route, "route_id")
                inserted_count += 1

    db.commit()
    logger.info("Routes seed complete: %d inserted, %d existing (total tracked: %d)", inserted_count, existing_count, len(route_map))
    return route_map


def seed_risk_events(db, route_map: Dict[Tuple[str, str], int]) -> int:
    """
    Load data/raw/risk_events.csv and insert into 'risk_events' table.
    Resolves 'affected_route' string (e.g. 'Beira-Dhamra') to affected_route_id (integer FK).
    Natural key: (date, event_type, description).
    """
    logger.info("--- Seeding Risk Events ---")
    expected_headers = [
        "date", "event_type", "description", "affected_route",
        "severity_level", "historical_price_impact_pct"
    ]

    # Build lookup for route strings formatted as 'Origin-Destination'
    route_str_lookup: Dict[str, int] = {
        f"{orig}-{dest}": r_id for (orig, dest), r_id in route_map.items()
    }

    inserted_count = 0
    existing_count = 0

    with open(RISK_EVENTS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected_headers:
            raise ValueError(
                f"risk_events.csv header mismatch. Expected {expected_headers}, got {reader.fieldnames}"
            )

        for row_idx, row in enumerate(reader, start=1):
            date_str = row["date"].strip()
            event_type = row["event_type"].strip()
            description = row["description"].strip()
            affected_route_str = row["affected_route"].strip() if row.get("affected_route") else ""
            severity_level = row["severity_level"].strip()
            impact_str = row["historical_price_impact_pct"].strip() if row.get("historical_price_impact_pct") else None

            # Non-null validation for required fields
            if not all([date_str, event_type, description, severity_level]):
                raise ValueError(f"risk_events.csv row {row_idx} contains empty required field: {row}")

            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Resolve affected_route_id FK
            affected_route_id: Optional[int] = None
            if affected_route_str:
                if affected_route_str in route_str_lookup:
                    affected_route_id = route_str_lookup[affected_route_str]
                else:
                    raise ValueError(
                        f"risk_events.csv row {row_idx}: affected_route '{affected_route_str}' "
                        f"does not match any recognized route! Available routes: {list(route_str_lookup.keys())}"
                    )

            # Check existing record by natural key (date, event_type, description)
            existing = db.query(RiskEvent).filter(
                RiskEvent.date == event_date,
                RiskEvent.event_type == event_type,
                RiskEvent.description == description,
            ).first()

            if existing:
                existing_count += 1
            else:
                new_event = RiskEvent(
                    date=event_date,
                    event_type=event_type,
                    description=description,
                    affected_route_id=affected_route_id,
                    severity_level=severity_level,
                    historical_price_impact_pct=Decimal(impact_str) if impact_str else None,
                )
                db.add(new_event)
                inserted_count += 1

    db.commit()
    logger.info("RiskEvents seed complete: %d inserted, %d existing (total: %d)", inserted_count, existing_count, inserted_count + existing_count)
    return inserted_count


def seed_all_reference_data() -> Dict[str, int]:
    """
    Run full reference data seeding pipeline.
    Returns dictionary with counts of rows in database after seeding.
    """
    verify_raw_files_exist()

    db = SessionLocal()
    try:
        port_map = seed_ports(db)
        vessel_map = seed_vessel_types(db)
        route_map = seed_routes(db, port_map)
        seed_risk_events(db, route_map)

        final_counts = {
            "ports": db.query(Port).count(),
            "vessel_types": db.query(VesselType).count(),
            "routes": db.query(Route).count(),
            "risk_events": db.query(RiskEvent).count(),
        }
        logger.info("Final table counts in Neon database: %s", final_counts)
        return final_counts
    except Exception as exc:
        db.rollback()
        logger.error("Seeding failed: %s", exc, exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        counts = seed_all_reference_data()
        print(f"SUCCESS: Seeded reference data successfully. Table counts: {counts}")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Seeding failed: {e}")
        sys.exit(1)
