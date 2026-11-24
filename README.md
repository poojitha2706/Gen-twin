# GenTwin Vision

A prototype digital twin for smart manufacturing. Cameras watch machines, a vision model detects
defects, a retrieval and decision module explains likely causes and decides between automatic
handling and human escalation, and a 3D dashboard shows the live state of every machine.

This is a software proof of concept. The machines are simulated from public datasets, the
incident history is synthetic, and all "autonomous" actions are limited to logging, alerting and
escalation. Nothing controls physical equipment.

## How it fits together
```
images -> cv-module (YOLOv8) -> POST /anomaly -> backend (FastAPI, database)
                                                    ^   |
              rag-module/adapter.py  <--------------+   +--> frontend (3D dashboard)
              reads new detections, retrieves similar incidents, applies the decision policy,
              and posts cause, confidence and action to /anomaly/{id}/cause
```

| Folder | Role | Author |
|---|---|---|
| `cv-module` | Defect detection and reporting | Poojitha |
| `backend` | Central hub: API, machine state, history | Chanikya |
| `rag-module` | Incident retrieval, risk and decision policy, adapter | Raviteja (adapter and incident data: Poojitha) |
| `frontend` | 3D digital twin dashboard | Srujana (render-mode data source: Poojitha) |

## Run the demo
Start each in its own terminal. Every module has its own setup steps in its README.
1. **Backend:** deployed at https://gen-twin.onrender.com (the free server sleeps, so open
   `/machines` a minute early). Locally: `cd backend`, `uvicorn main:app --port 8000`.
2. **Adapter:** `cd rag-module`, set `BACKEND_BASE_URL`, run `python adapter.py`.
3. **Dashboard:** `cd frontend`, create `.env` with `VITE_DATA_SOURCE=render` and
   `VITE_API_URL=<backend url>`, then `npm install` and `npm run dev`.
4. **Detector:** `cd cv-module`, run `python detect.py <images> --machine machine_01 --loop`.

## Known limits
- The incident history and causes are synthetic, and retrieval is TF-IDF, not a language model.
- The risk term in the decision policy is a placeholder based on recent detection counts.
- Crazing is detected poorly (recall 0.27).
- The twin reads state from the cameras and does not send commands back to the machines.
