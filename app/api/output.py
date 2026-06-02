import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.domain import IngestedPayload, MachineState, DerivedStatus
from app.api import schemas

router = APIRouter(prefix="/api/v1/output", tags=["Output"])

@router.get("/status/{payload_id}", response_model=schemas.PayloadStatusResponse)
def get_payload_status(payload_id: str, db: Session = Depends(get_db)):
    """Check the processing status of an ingested payload."""
    payload = db.query(IngestedPayload).filter(IngestedPayload.payload_id == payload_id).first()
    if not payload:
        raise HTTPException(status_code=404, detail="Payload not found")
        
    return schemas.PayloadStatusResponse(
        payload_id=payload.payload_id,
        status=payload.status.name if payload.status else "UNKNOWN",
        error_message=payload.error_message,
        received_at=payload.received_at,
        processed_at=payload.processed_at
    )

@router.get("/machines/{machine_id}", response_model=schemas.MachineStateResponse)
def get_machine_state(machine_id: str, db: Session = Depends(get_db)):
    """Get the current operational state of a single machine."""
    state = db.query(MachineState).filter(MachineState.machine_id == machine_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    reason_codes = []
    if state.reason_codes:
        try:
            reason_codes = json.loads(state.reason_codes)
        except:
            reason_codes = [state.reason_codes]
            
    source_event_refs = []
    if state.source_event_refs:
        try:
            source_event_refs = json.loads(state.source_event_refs)
        except:
            source_event_refs = [state.source_event_refs]
            
    return schemas.MachineStateResponse(
        machine_id=state.machine_id,
        plant_id=state.plant_id or "UNKNOWN",
        derived_status=state.derived_status.name if state.derived_status else "UNKNOWN",
        needs_attention=bool(state.needs_attention),
        attention_level=state.attention_level.name if state.attention_level else "UNKNOWN",
        reason_codes=reason_codes,
        latest_relevant_event_time=state.latest_relevant_event_time,
        source_event_refs=source_event_refs
    )

@router.get("/machines/{machine_id}/events", response_model=list[schemas.NormalizedEventResponse])
def get_machine_events(machine_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """Get the detailed historical normalized events (sensor readings, etc) for a single machine."""
    from app.models.domain import NormalizedEvent
    events = db.query(NormalizedEvent)\
        .filter(NormalizedEvent.machine_id == machine_id)\
        .order_by(NormalizedEvent.event_time.desc())\
        .limit(limit)\
        .all()
        
    if not events:
        raise HTTPException(status_code=404, detail="No events found for this machine")
        
    return [
        schemas.NormalizedEventResponse(
            event_id=e.event_id,
            machine_id=e.machine_id,
            event_time=e.event_time,
            vendor=e.vendor,
            temperature_c=e.temperature_c,
            vibration_mm_s=e.vibration_mm_s,
            normalized_severity=e.normalized_severity.name if e.normalized_severity else None,
            inspection_note=e.inspection_note
        ) for e in events
    ]

@router.get("/plants/{plant_id}/summary", response_model=schemas.PlantSummaryResponse)
def get_plant_summary(plant_id: str, db: Session = Depends(get_db)):
    """Get an aggregated summary of all machines in a specific plant."""
    states = db.query(MachineState).filter(MachineState.plant_id == plant_id).all()
    
    total = len(states)
    if total == 0:
        raise HTTPException(status_code=404, detail="Plant not found or has no machines")
        
    needing_attention = sum(1 for s in states if s.needs_attention)
    critical_machines_list = [s.machine_id for s in states if s.derived_status == DerivedStatus.CRITICAL]
    
    # Line groupings for attention
    lines = {}
    for s in states:
        if s.needs_attention:
            lines[s.line_id] = lines.get(s.line_id, 0) + 1
            
    lines_summary = [schemas.LineSummary(line_id=k, machines_needing_attention=v) for k, v in lines.items()]
    lines_summary.sort(key=lambda x: x.machines_needing_attention, reverse=True)
    
    return schemas.PlantSummaryResponse(
        plant_id=plant_id,
        total_machines=total,
        machines_needing_attention=needing_attention,
        critical_machines_list=critical_machines_list,
        lines_needing_attention=lines_summary
    )
