# Mosaic - Professional Financial Model Generator

## Original Problem Statement
Build a web app called "Mosaic" for investment professionals that takes an Indian stock ticker as input and generates:
1. A professional-grade financial model in `.xlsx` format
2. A detailed investment thesis

## Core Requirements

### Input
- Single NSE/BSE stock ticker

### Core Pipeline (8 Steps)
1. **Company Identification** - Identify company, sector, and metadata
2. **Annual Financial Data** - Scrape from Screener.in
3. **Operational Metrics** - Extract quarterly KPIs from BSE presentations
4. **Management Commentary** - Process concall transcripts
5. **Assumptions Generation** - Use Claude AI to generate forecast assumptions
6. **Excel Model Generation** - Create multi-sheet `.xlsx` file
7. **Valuation** - Perform RIV, Peer Comps, DDM analysis
8. **Thesis Generation** - Write structured investment thesis

### Knowledge Base
- Sector-specific logic in editable Markdown files at `/knowledge`
- Ships with detailed `banks.md` file

### Frontend Features
- Landing page with ticker input
- Processing page with live pipeline status
- Results page with thesis and Excel download
- Jobs dashboard showing all running/past jobs

### Admin
- Password-protected `/admin` page for editing sector knowledge files

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI (Python), Motor (async MongoDB)
- **AI**: Claude Sonnet 4.5 via Emergent LLM Key
- **Scraping**: Playwright
- **Database**: MongoDB

## What's Been Implemented

### Completed (as of 2026-02-22)
- [x] Full-stack application scaffolding (React + FastAPI)
- [x] 8-step async pipeline in `pipeline_manager.py`
- [x] WebSocket real-time progress updates
- [x] File-based caching for step outputs
- [x] Jobs dashboard (view all jobs, status, progress)
- [x] Retry functionality for failed jobs
- [x] Abort job functionality (backend + frontend)
- [x] **Real-Time Activity Log** - Live display of API calls, LLM thinking, and data processing
- [x] Claude AI integration for reasoning steps

### In Progress
- [ ] Step 5 performance optimization (currently ~50s for Claude API calls)

### Not Started / Placeholder
- [ ] Step 6: Full Excel model generation (currently placeholder)
- [ ] Step 7: Complete valuation implementation
- [ ] Step 8: Complete thesis generation
- [ ] Admin page backend for knowledge file management
- [ ] Download Excel button on Results page

## Key Files

### Backend
- `backend/services/pipeline_manager.py` - Core pipeline orchestrator
- `backend/services/claude_service.py` - Claude AI integration with activity broadcasting
- `backend/services/websocket_manager.py` - WebSocket manager with activity_log support
- `backend/services/cache_service.py` - File-based cache management
- `backend/routes/generate.py` - API endpoints

### Frontend
- `frontend/src/pages/Landing.jsx` - Home page with ticker input
- `frontend/src/pages/Processing.jsx` - Real-time pipeline status + Activity Log
- `frontend/src/pages/Jobs.jsx` - Jobs dashboard with Abort button
- `frontend/src/pages/Results.jsx` - Results display
- `frontend/src/components/JobsList.jsx` - Jobs list component

## API Endpoints
- `POST /api/generate` - Create new job
- `GET /api/generate/jobs` - List all jobs
- `GET /api/generate/progress/{job_id}` - Get job progress
- `POST /api/generate/retry/{job_id}` - Retry failed job
- `POST /api/generate/abort/{job_id}` - Abort running job
- `WS /api/generate/ws/{job_id}` - WebSocket for real-time updates

## Database Schema
```json
{
  "jobs": {
    "id": "string",
    "ticker": "string",
    "status": "pending|processing|completed|failed",
    "current_step": "int",
    "steps": "array",
    "error": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

## Prioritized Backlog

### P0 (Critical)
- Step 6: Excel model generation with openpyxl

### P1 (High)
- Step 7 & 8: Complete valuation and thesis implementation
- Improve scraping reliability

### P2 (Medium)
- Admin page backend for knowledge files
- Download Excel button
- Step 5 performance optimization

### P3 (Low/Future)
- Additional sector knowledge files
- User authentication
- Export to PDF
