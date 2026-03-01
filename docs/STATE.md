# Cantor Project State

## 1. Project Overview
- **Name**: Cantor
- **Architecture**: Scheme A (Go + Python Microservices)
- **Goal**: B2B/B2C Commercial Cloud Phone Agent Scheduling Platform.

## 2. Current Phase: Auth System Implementation
- [x] Core infrastructure (Gateway + Brain)
- [x] Multi-tenant auth design (docs)
- [ ] **Database Models** - SQLAlchemy models for auth tables
- [ ] **Database Migrations** - Alembic setup
- [ ] **Auth Service** - JWT sign/verify/refresh
- [ ] **API Key Service** - Create/validate/revoke
- [ ] **User API** - Register/Login/Logout
- [ ] **Organization API** - CRUD
- [ ] **Workspace API** - CRUD + member management
- [ ] **Permission Middleware** - RBAC enforcement
- [ ] IaaS API Integration (Blocked - needs credentials)

## 3. Active Sub-agents
1. **Auth Implementation Agent** - Building auth services and APIs

## 4. Quick Start
```bash
./scripts/start-all.sh
```

## 5. Blockers
- IaaS API credentials (waiting)
- RTC API docs (skipped)
