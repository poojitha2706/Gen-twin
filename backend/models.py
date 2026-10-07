import datetime
from sqlalchemy import Column, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(String, primary_key=True)
    machine_id = Column(String, index=True)
    defect_class = Column(String)
    confidence = Column(Float)
    cause = Column(Text, nullable=True)              # filled later by the RAG module
    cause_confidence = Column(Float, nullable=True)
    action = Column(String, default="pending")       # pending | auto_logged | escalated
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class Machine(Base):
    __tablename__ = "machines"

    machine_id = Column(String, primary_key=True)
    status = Column(String, default="normal")        # normal | anomaly_detected
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
