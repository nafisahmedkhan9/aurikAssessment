import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.domain import IngestedPayload, ProcessingStatus, NormalizedEvent, SeverityLevel, MachineState, DerivedStatus

# --- Normalization Helpers ---

def parse_iso_time(ts_str: str) -> datetime:
    """Handles PulseForge ISO strings ending with Z."""
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str)

def fahrenheit_to_celsius(f: float) -> float:
    """Unit normalization for ThermexWatch."""
    return (f - 32.0) * 5.0 / 9.0

def map_pulseforge_severity(severity_str: str) -> SeverityLevel:
    """Enum mapping for PulseForge string severities."""
    mapping = {
        "nominal": SeverityLevel.NOMINAL,
        "low": SeverityLevel.LOW,
        "moderate": SeverityLevel.MODERATE,
        "high": SeverityLevel.HIGH,
        "critical": SeverityLevel.CRITICAL
    }
    return mapping.get(severity_str.lower(), SeverityLevel.NOMINAL)

# --- Vendor Normalization Routines ---

def normalize_pulseforge(db: Session, payload: IngestedPayload, raw_dict: dict):
    events = raw_dict.get("events", [])
    for event in events:
        norm = NormalizedEvent(
            event_id=event.get("event_id") or str(uuid.uuid4()),
            payload_id=payload.payload_id,
            machine_id=event.get("machine_id"),
            event_time=parse_iso_time(event.get("event_time")),
            vendor="PulseForge",
            temperature_c=event.get("temperature_c"),
            vibration_mm_s=event.get("vibration_mm_s"),
            normalized_severity=map_pulseforge_severity(event.get("severity", "nominal"))
        )
        db.merge(norm)

def normalize_thermexwatch(db: Session, payload: IngestedPayload, raw_dict: dict):
    readings = raw_dict.get("readings", [])
    for reading in readings:
        ts_ms = reading.get("timestampMs", 0)
        dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
        
        temp_f = reading.get("temperature_f")
        temp_c = fahrenheit_to_celsius(temp_f) if temp_f is not None else None
        
        level = reading.get("level", 1)
        try:
            severity = SeverityLevel(level)
        except ValueError:
            severity = SeverityLevel.NOMINAL
        
        norm = NormalizedEvent(
            event_id=reading.get("readingId") or str(uuid.uuid4()),
            payload_id=payload.payload_id,
            machine_id=reading.get("assetCode"),
            event_time=dt,
            vendor="ThermexWatch",
            temperature_c=temp_c,
            vibration_mm_s=None,
            normalized_severity=severity
        )
        db.merge(norm)

def normalize_maintaflow(db: Session, payload: IngestedPayload, raw_dict: dict):
    records = raw_dict.get("records", [])
    for record in records:
        ts_str = record.get("recorded_at")
        dt = datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
        
        result = record.get("inspection_result")
        severity = SeverityLevel.NOMINAL
        if result == "minor_defect_found":
            severity = SeverityLevel.LOW
        elif result == "major_defect_found":
            severity = SeverityLevel.HIGH
            
        norm = NormalizedEvent(
            event_id=record.get("record_id") or str(uuid.uuid4()),
            payload_id=payload.payload_id,
            machine_id=record.get("machine_ref"),
            event_time=dt,
            vendor="MaintaFlow",
            temperature_c=None,
            vibration_mm_s=None,
            normalized_severity=severity,
            inspection_note=record.get("technician_note")
        )
        db.merge(norm)

# --- State Derivation Logic ---

def update_machine_state(db: Session, machine_id: str):
    """
    Deterministic logic to calculate the operational view of a machine 
    based on its most recent normalized events.
    """
    # 1. Get the most recent event for this machine
    latest_event = db.query(NormalizedEvent).filter(
        NormalizedEvent.machine_id == machine_id
    ).order_by(desc(NormalizedEvent.event_time)).first()
    
    if not latest_event:
        return
        
    # 2. Find or create the canonical MachineState
    state = db.query(MachineState).filter(MachineState.machine_id == machine_id).first()
    
    # Dynamically extract plant_id and line_id from the payload
    payload = db.query(IngestedPayload).filter(IngestedPayload.payload_id == latest_event.payload_id).first()
    plant_id = "UNKNOWN"
    line_id = "UNKNOWN"
    if payload:
        raw = json.loads(payload.raw_data)
        plant_id = raw.get("plant_id") or raw.get("site_code") or raw.get("factory_id") or "UNKNOWN"
        
        # Extract line_id from the specific event
        if latest_event.vendor == "PulseForge":
            for e in raw.get("events", []):
                if e.get("machine_id") == machine_id:
                    line_id = e.get("line_id", "UNKNOWN")
        elif latest_event.vendor == "ThermexWatch":
            for r in raw.get("readings", []):
                if r.get("assetCode") == machine_id:
                    line_id = r.get("productionLine", "UNKNOWN")
        elif latest_event.vendor == "MaintaFlow":
            for r in raw.get("records", []):
                if r.get("machine_ref") == machine_id:
                    line_id = r.get("line_ref", "UNKNOWN")

        # Normalize line_id to always be "LINE-X" (e.g., convert "A" to "LINE-A", "line-B" to "LINE-B")
        if line_id != "UNKNOWN":
            clean_line = str(line_id).strip().upper()
            if clean_line.startswith("LINE-"):
                line_id = clean_line
            elif clean_line.startswith("LINE "):
                line_id = clean_line.replace("LINE ", "LINE-")
            else:
                line_id = f"LINE-{clean_line}"

    if not state:
        state = MachineState(
            machine_id=machine_id,
            plant_id=plant_id,
            line_id=line_id
        )
        db.add(state)
    else:
        state.plant_id = plant_id
        state.line_id = line_id
        
    # 3. Apply Deterministic Rules
    severity = latest_event.normalized_severity or SeverityLevel.NOMINAL
    
    state.attention_level = severity
    state.needs_attention = bool(severity >= SeverityLevel.MODERATE)
    
    if severity == SeverityLevel.CRITICAL:
        state.derived_status = DerivedStatus.CRITICAL
    elif severity >= SeverityLevel.MODERATE:
        state.derived_status = DerivedStatus.ATTENTION_REQUIRED
    else:
        state.derived_status = DerivedStatus.NOMINAL
        
    # 4. Update Traceability & Freshness
    state.latest_relevant_event_time = latest_event.event_time
    state.processing_status = "active"
    state.source_event_refs = json.dumps([latest_event.event_id])
    state.last_processed_at = datetime.utcnow()
    
    # Generate simple reason codes
    reasons = [f"Vendor [{latest_event.vendor}] reported severity [{severity.name}]"]
    if latest_event.inspection_note:
        reasons.append("Qualitative inspection note present")
    state.reason_codes = json.dumps(reasons)


# --- Main Entry Point ---

def process_payload_task(payload_id: str):
    db: Session = SessionLocal()
    try:
        payload = db.query(IngestedPayload).filter(IngestedPayload.payload_id == payload_id).first()
        if not payload: return
        
        raw_dict = json.loads(payload.raw_data)
        
        # 1. Normalize
        if payload.vendor == "PulseForge":
            normalize_pulseforge(db, payload, raw_dict)
        elif payload.vendor == "ThermexWatch":
            normalize_thermexwatch(db, payload, raw_dict)
        elif payload.vendor == "MaintaFlow":
            normalize_maintaflow(db, payload, raw_dict)
            
        db.flush() # Ensure events are written so we can query them
        
        # 2. Compute State
        machines_updated = db.query(NormalizedEvent.machine_id).filter(
            NormalizedEvent.payload_id == payload_id
        ).distinct().all()
        
        for (m_id,) in machines_updated:
            if m_id:
                update_machine_state(db, m_id)
                
        # 3. Complete
        payload.status = ProcessingStatus.PROCESSED
        payload.processed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        payload = db.query(IngestedPayload).filter(IngestedPayload.payload_id == payload_id).first()
        if payload:
            payload.status = ProcessingStatus.FAILED
            payload.error_message = str(e)
            payload.processed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
