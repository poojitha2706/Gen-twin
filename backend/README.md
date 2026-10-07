# GenTwin Vision - Backend

The central hub: CV, RAG and the dashboard all talk through this service.

## Run
```
python -m venv venv
venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

## Endpoints
| Endpoint | Used by | Purpose |
|---|---|---|
| POST /anomaly  {machine_id, defect_class, confidence} | CV module | Save a detection, mark machine anomaly_detected |
| POST /anomaly/{id}/cause  {cause, cause_confidence, action} | RAG module | Store cause and decision (auto_logged / escalated) |
| GET /machines | Dashboard | Live state of all machines |
| GET /machines/{id}/history | Dashboard, RAG | Past detections for a machine |
| POST /machines/{id}/reset | Dashboard | Set machine back to normal |
| WebSocket /ws | Dashboard | Live messages: new_anomaly, cause_update, machine_reset |

## Testing
- Fake CV sender: `python send_test.py`
- Automated test: `pip install httpx` then `python test_api.py`

## Config
Copy `.env.example` to `.env`. Only DATABASE_URL is needed (SQLite by default; PostgreSQL later).
