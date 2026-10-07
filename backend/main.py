import json
import uuid
import datetime
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db
from models import Anomaly, Machine
from schemas import AnomalyIn, AnomalyOut, MachineOut, CauseUpdateIn

app = FastAPI(title="GenTwin Vision Backend")

# Lets the dashboard (a different port/domain) call this API.
# Tighten this to your frontend URL when you deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: List[WebSocket] = []


async def broadcast_update(message: dict):
    """Send a message to every connected dashboard."""
    dead = []
    for client in connected_clients:
        try:
            await client.send_text(json.dumps(message, default=str))
        except Exception:
            dead.append(client)
    for client in dead:
        if client in connected_clients:
            connected_clients.remove(client)


@app.get("/")
def health():
    return {"status": "ok", "service": "GenTwin Vision Backend"}


@app.post("/anomaly", response_model=AnomalyOut)
async def receive_anomaly(data: AnomalyIn, db: Session = Depends(get_db)):
    """Called by the CV module whenever it detects something."""
    record = Anomaly(
        id=str(uuid.uuid4()),
        machine_id=data.machine_id,
        defect_class=data.defect_class,
        confidence=data.confidence,
        action="pending",
    )
    db.add(record)

    # update (or create) the machine's live status
    machine = db.query(Machine).filter(Machine.machine_id == data.machine_id).first()
    if not machine:
        machine = Machine(machine_id=data.machine_id)
        db.add(machine)
    machine.status = "anomaly_detected"
    machine.last_updated = datetime.datetime.utcnow()

    db.commit()
    db.refresh(record)

    payload = AnomalyOut.model_validate(record).model_dump(mode="json")
    await broadcast_update({"type": "new_anomaly", "data": payload})
    return record


@app.get("/machines", response_model=List[MachineOut])
def get_machines(db: Session = Depends(get_db)):
    return db.query(Machine).all()


@app.get("/machines/{machine_id}/history", response_model=List[AnomalyOut])
def get_machine_history(machine_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Anomaly)
        .filter(Anomaly.machine_id == machine_id)
        .order_by(Anomaly.timestamp.desc())
        .all()
    )


@app.post("/anomaly/{anomaly_id}/cause", response_model=AnomalyOut)
async def update_cause(anomaly_id: str, data: CauseUpdateIn, db: Session = Depends(get_db)):
    """Called by the RAG module once it has worked out the probable cause."""
    record = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    record.cause = data.cause
    record.cause_confidence = data.cause_confidence
    record.action = data.action
    db.commit()
    db.refresh(record)

    payload = AnomalyOut.model_validate(record).model_dump(mode="json")
    await broadcast_update({"type": "cause_update", "data": payload})
    return record


@app.post("/machines/{machine_id}/reset", response_model=MachineOut)
async def reset_machine(machine_id: str, db: Session = Depends(get_db)):
    """Sets a machine back to normal (for example after a human has fixed it)."""
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    machine.status = "normal"
    machine.last_updated = datetime.datetime.utcnow()
    db.commit()
    db.refresh(machine)
    payload = MachineOut.model_validate(machine).model_dump(mode="json")
    await broadcast_update({"type": "machine_reset", "data": payload})
    return machine


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()   # keeps the connection open
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
