import datetime
import enum
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Float, Enum
from app.core.database import Base

class SeverityLevel(int, enum.Enum):
    NOMINAL = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    CRITICAL = 5

class DerivedStatus(str, enum.Enum):
    NOMINAL = "nominal"
    ATTENTION_REQUIRED = "attention_required"
    CRITICAL = "critical"
    MAINTENANCE_NEEDED = "maintenance_needed"

class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"

class IngestedPayload(Base):
    """
    Stores raw incoming payloads for idempotency, traceability, and asynchronous processing.
    """
    __tablename__ = "ingested_payloads"

    payload_id = Column(String, primary_key=True, index=True)
    vendor = Column(String, index=True)  
    raw_data = Column(Text)  
    status = Column(Enum(ProcessingStatus, name="processing_status_enum"), default=ProcessingStatus.PENDING) 
    received_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

class NormalizedEvent(Base):
    """
    Stores the canonical, normalized version of every individual event/reading.
    Addresses: unit normalization, timestamp normalization, field mapping.
    """
    __tablename__ = "normalized_events"
    
    event_id = Column(String, primary_key=True, index=True)
    payload_id = Column(String, index=True)
    machine_id = Column(String, index=True)
    
    event_time = Column(DateTime, index=True)
    vendor = Column(String)
    
    temperature_c = Column(Float, nullable=True)
    vibration_mm_s = Column(Float, nullable=True)
    normalized_severity = Column(Enum(SeverityLevel, name="severity_level_enum"), nullable=True)
    
    inspection_note = Column(Text, nullable=True)

class MachineState(Base):
    """
    The canonical representation of a machine's current operational state.
    This fulfills the requirement for the machine operational attention view.
    """
    __tablename__ = "machine_states"

    machine_id = Column(String, primary_key=True, index=True)
    plant_id = Column(String, index=True)
    line_id = Column(String, index=True)
    
    derived_status = Column(Enum(DerivedStatus, name="derived_status_enum"))
    needs_attention = Column(Boolean, default=False)
    attention_level = Column(Enum(SeverityLevel, name="severity_level_enum", create_type=False))
    reason_codes = Column(Text)
    
    latest_relevant_event_time = Column(DateTime)
    processing_status = Column(String)
    source_event_refs = Column(Text)
    last_processed_at = Column(DateTime, default=datetime.datetime.utcnow)
