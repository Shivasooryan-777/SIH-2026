"""
Reference / Master Data API Router
===================================
Provides read-only master data endpoints for frontend consumers:
- GET /api/ports -> full Ports table
- GET /api/vessel-types -> full VesselTypes table
- GET /api/routes -> full Routes table with resolved port names & countries
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, aliased

from backend.app.database import get_db
from backend.app.models import Port, Route, VesselType

router = APIRouter(tags=["Reference Data"])


# =============================================================================
# Response Schemas
# =============================================================================

class PortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    port_id: int
    name: str
    country: str
    port_role: str
    max_loa_m: float
    max_beam_m: float
    baseline_draft_m: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VesselTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vessel_type_id: int
    name: str
    min_dwt: int
    max_dwt: int
    required_draft_m: float
    typical_loa_m: float
    typical_beam_m: float
    standard_speed_knots: float
    fuel_curve_coef: float


class RouteResponse(BaseModel):
    route_id: int
    origin_port_id: int
    origin_port_name: str
    origin_country: str
    destination_port_id: int
    destination_port_name: str
    destination_country: str
    distance_nm: int
    typical_transit_days: float


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/ports", response_model=List[PortResponse], summary="Full Ports Master Table")
def get_all_ports(db: Session = Depends(get_db)):
    """Return all ports (origins and destinations) sorted by role and name."""
    ports = db.query(Port).order_by(Port.port_role.desc(), Port.name.asc()).all()
    return [
        PortResponse(
            port_id=p.port_id,
            name=p.name,
            country=p.country,
            port_role=p.port_role,
            max_loa_m=float(p.max_loa_m),
            max_beam_m=float(p.max_beam_m),
            baseline_draft_m=float(p.baseline_draft_m),
            latitude=float(p.latitude) if p.latitude is not None else None,
            longitude=float(p.longitude) if p.longitude is not None else None,
        )
        for p in ports
    ]


@router.get("/vessel-types", response_model=List[VesselTypeResponse], summary="Full VesselTypes Master Table")
def get_all_vessel_types(db: Session = Depends(get_db)):
    """Return all vessel classes ordered by min_dwt ascending."""
    vessel_types = db.query(VesselType).order_by(VesselType.min_dwt.asc()).all()
    return [
        VesselTypeResponse(
            vessel_type_id=vt.vessel_type_id,
            name=vt.name,
            min_dwt=vt.min_dwt,
            max_dwt=vt.max_dwt,
            required_draft_m=float(vt.required_draft_m),
            typical_loa_m=float(vt.typical_loa_m),
            typical_beam_m=float(vt.typical_beam_m),
            standard_speed_knots=float(vt.standard_speed_knots),
            fuel_curve_coef=float(vt.fuel_curve_coef),
        )
        for vt in vessel_types
    ]


@router.get("/routes", response_model=List[RouteResponse], summary="Full Routes Master Table with Resolved Port Names")
def get_all_routes(db: Session = Depends(get_db)):
    """Return all routes with resolved origin and destination port names and countries."""
    origin_port = aliased(Port)
    dest_port = aliased(Port)

    query = (
        db.query(
            Route.route_id,
            Route.origin_port_id,
            origin_port.name.label("origin_name"),
            origin_port.country.label("origin_country"),
            Route.destination_port_id,
            dest_port.name.label("dest_name"),
            dest_port.country.label("dest_country"),
            Route.distance_nm,
            Route.typical_transit_days,
        )
        .join(origin_port, Route.origin_port_id == origin_port.port_id)
        .join(dest_port, Route.destination_port_id == dest_port.port_id)
        .order_by(Route.route_id.asc())
        .all()
    )

    return [
        RouteResponse(
            route_id=row.route_id,
            origin_port_id=row.origin_port_id,
            origin_port_name=row.origin_name,
            origin_country=row.origin_country,
            destination_port_id=row.destination_port_id,
            destination_port_name=row.dest_name,
            destination_country=row.dest_country,
            distance_nm=row.distance_nm,
            typical_transit_days=float(row.typical_transit_days),
        )
        for row in query
    ]
