import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AnomalyIn(BaseModel):
    machine_id: str
    defect_class: str
    confidence: float


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    machine_id: str
    defect_class: str
    confidence: float
    cause: Optional[str] = None
    cause_confidence: Optional[float] = None
    action: str
    timestamp: datetime.datetime


class MachineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    machine_id: str
    status: str
    last_updated: datetime.datetime


class CauseUpdateIn(BaseModel):
    cause: str
    cause_confidence: float
    action: str   # auto_logged | escalated
