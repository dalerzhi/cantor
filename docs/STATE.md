# Cantor Project State

## 1. Project Overview
- **Name**: Cantor
- **Architecture**: Scheme A (Go + Python Microservices)
- **Goal**: B-End Cloud Phone Agent Scheduling Platform.

## 2. Current Phase: Core Features Complete ✅
- [x] Create project repository and directory structure.
- [x] Migrate and refine PRD and ARCHITECTURE docs.
- [x] Setup Hourly Reporting Cron Job.
- [x] Parse IaaS API documentation (Done).
- [x] Develop `cantor-gateway` (Go) - WebSocket + Redis Pub/Sub (Done).
- [x] Develop `cantor-brain` (Python) - FastAPI + Redis Client + Core APIs (Done).
- [x] Integration Testing - Scripts and protocol validation (Done).
- [ ] IaaS API Integration (Next Phase - Requires real API credentials).

## 3. Sub-agent Roles & Status
1. **Manager (Main Session)**: Orchestrates tasks, updates `STATE.md`, communicates with user.
2. **Doc Reader Agent**: ✅ Done. Extracted IaaS API spec to `docs/iaas_api_spec.md`.
3. **Gateway Dev Agent**: ✅ Done. Implemented WebSocket + Redis Pub/Sub in Go.
4. **Brain Dev Agent**: ✅ Done. Implemented Redis client and event handling in Python.
5. **Backend Dev Agent**: ✅ Done. Implemented Device/CantorInstance/TaskQueue APIs.
6. **Integration Agent**: ✅ Done. Created E2E test scripts and validated protocol.

## 4. Quick Start
```bash
# Start all services
./scripts/start-all.sh

# Run E2E tests
./scripts/test-e2e.py

# Stop all services
./scripts/stop-all.sh
```

## 5. API Endpoints
- **Gateway WebSocket**: `ws://localhost:8766/ws?device_id={id}`
- **Brain API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`

## 6. Blockers / Dependencies
- RTC API documentation pending (skipped for now).
- IaaS API integration requires real API credentials.
