import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.domain import MachineState, IngestedPayload, NormalizedEvent

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5433/aurik"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

payloads = db.query(IngestedPayload).all()
print("--- PAYLOADS ---")
for p in payloads:
    print(f"ID: {p.payload_id}, Status: {p.status.name if p.status else None}, Error: {p.error_message}")

events = db.query(NormalizedEvent).all()
print("\n--- NORMALIZED EVENTS ---")
for e in events:
    print(f"Machine: {e.machine_id}, Severity: {e.normalized_severity}")

states = db.query(MachineState).all()
print("\n--- MACHINE STATES ---")
for s in states:
    print(f"Machine: {s.machine_id}, Needs Attention: {s.needs_attention}, Level: {s.attention_level.name if s.attention_level else None}")

db.close()
