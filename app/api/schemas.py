from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

# --- PulseForge Schemas ---
class PulseForgeEvent(BaseModel):
    event_id: str = Field(..., min_length=1)
    machine_id: str = Field(..., min_length=1)
    line_id: str = Field(..., min_length=1)
    event_time: datetime
    event_type: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    vibration_mm_s: Optional[float] = None
    temperature_c: Optional[float] = None
    machine_state: Optional[str] = None
    sensor_health: Optional[float] = None
    vendor_confidence: Optional[float] = None

class PulseForgePayload(BaseModel):
    vendor: str = Field(..., min_length=1)
    plant_id: str = Field(..., min_length=1)
    batch_generated_at: datetime
    events: List[PulseForgeEvent]

# --- ThermexWatch Schemas ---
class ThermexWatchReading(BaseModel):
    readingId: str = Field(..., min_length=1)
    assetCode: str = Field(..., min_length=1)
    productionLine: str = Field(..., min_length=1)
    timestampMs: int
    alertCode: str = Field(..., min_length=1)
    level: int
    vibration_g: Optional[float] = None
    temperature_f: Optional[float] = None
    power_kw: Optional[float] = None
    is_active: Optional[bool] = None
    signal_quality: Optional[str] = None

class ThermexWatchPayload(BaseModel):
    source: str = Field(..., min_length=1)
    site_code: str = Field(..., min_length=1)
    response_time_epoch_ms: int
    readings: List[ThermexWatchReading]

# --- MaintaFlow Schemas ---
class MaintaFlowRecord(BaseModel):
    record_id: str = Field(..., min_length=1)
    machine_ref: str = Field(..., min_length=1)
    line_ref: str = Field(..., min_length=1)
    recorded_at: str = Field(..., min_length=1)
    record_type: str = Field(..., min_length=1)
    inspection_result: Optional[str] = None
    maintenance_status: Optional[str] = None
    days_since_last_service: Optional[int] = None
    technician_note: Optional[str] = None
    manual_confidence: Optional[str] = None

class MaintaFlowPayload(BaseModel):
    provider_name: str = Field(..., min_length=1)
    factory_id: str = Field(..., min_length=1)
    records: List[MaintaFlowRecord]

# --- Response Schemas ---
class IngestionResponse(BaseModel):
    payload_id: str
    message: str

class PayloadStatusResponse(BaseModel):
    payload_id: str
    status: str
    error_message: Optional[str] = None
    received_at: datetime
    processed_at: Optional[datetime] = None

class MachineStateResponse(BaseModel):
    machine_id: str
    plant_id: str
    derived_status: str
    needs_attention: bool
    attention_level: str
    reason_codes: List[str]
    latest_relevant_event_time: Optional[datetime]
    source_event_refs: List[str]

class LineSummary(BaseModel):
    line_id: str
    machines_needing_attention: int

class PlantSummaryResponse(BaseModel):
    plant_id: str
    total_machines: int
    machines_needing_attention: int
    critical_machines_list: List[str]
    lines_needing_attention: List[LineSummary]
