# Mosaic - Financial Model Generator for Indian Equities

## Product Overview
Mosaic is a professional-grade financial model generator for Indian stock market analysis. It takes an NSE/BSE ticker as input and produces:
1. A fully-linked Excel financial model (.xlsx) with historical data and 5-year projections
2. A detailed AI-generated investment thesis with actual metrics from investor presentations and concall transcripts

## Core Requirements
- **Input:** Single NSE/BSE stock ticker
- **Output:** 
  - Excel model with P&L, Balance Sheet, ROE Tree, Valuation (all formula-driven)
  - Investment thesis with recommendation and target price, citing actual metrics

## Technical Architecture

### Backend (FastAPI)
- **Pipeline Manager:** Supports both sequential (legacy) and agentic modes
- **Agentic Mode:** Claude AI autonomously uses tools to build financial models
- **Scraper Service:** Playwright-based scraping from Screener.in + yfinance for prices
- **PDF Extractor:** Downloads and parses investor presentations, annual reports, and concall transcripts
- **Claude AI Integration:** Tool-use API via LiteLLM + Emergent LLM gateway
- **Excel Generator:** openpyxl-based model with formulas
- **Cache Service:** Local file caching for step results
- **WebSocket Manager:** Real-time progress updates

### Frontend (React)
- **Landing Page:** Professional dark theme, ticker input with validation, tools showcase
- **Processing Page:** Live activity log via WebSockets, prominent tool call display
- **Results Page:** Thesis display (Bull/Bear Case, Catalysts), valuation metrics, Excel download
- **Jobs Page:** Dashboard for all jobs
- **Admin Page:** CRUD for sector knowledge files
- **Cache Viewer:** View cached data per ticker

### Database (MongoDB)
- Jobs collection for job metadata

## What's Been Implemented

### Completed Features (Feb 2025)

#### UI/UX Overhaul (Feb 24, 2025)
- [x] Redesigned Landing page with professional dark theme (#0a0e17)
- [x] Added "Integrated Tools" section showcasing 6 AI tools
- [x] Stats bar (10+ Excel Sheets, 5Y Forecast, 6 AI Tools, <5min)
- [x] Redesigned Processing page with prominent tool calls and sidebar
- [x] Redesigned Results page with Bull/Bear Case, Catalysts display
- [x] Fixed thesis tab to show actual content (not placeholder)

#### Bug Fixes (Feb 24, 2025)
- [x] Fixed current_price showing as 0 on Results page
  - Modified `mosaic_agent.py` to read stock_price from cache if not in collected data
  - Modified `pipeline_manager.py` to pull current_price from multiple sources
  - Modified `agent_tools.py` to use valuation data as fallback for stock price
- [x] Fixed empty Excel sheets - now skips sheets with no data
- [x] Fixed market_cap sometimes showing as 0
  - Modified `scraper_service.py` to fetch market_cap from Screener.in if Yahoo Finance doesn't return it
  - Now combines best data from both Yahoo Finance (real-time price) and Screener.in (reliable market_cap)

#### Agentic Architecture (Feb 2025)
- [x] Fixed Claude tool-use API integration via LiteLLM + Emergent gateway
- [x] Created mosaic_agent.py with full agentic loop
- [x] Created agent_tools.py with 11 tools (scraping, PDF parsing, knowledge base, Excel generation)
- [x] Converted Anthropic tool format to OpenAI format for LiteLLM compatibility
- [x] Added retry logic for transient LLM errors (502, 503, timeouts)
- [x] Pipeline manager supports MOSAIC_AGENTIC_MODE flag
- [x] Legacy sequential pipeline preserved as fallback (set MOSAIC_AGENTIC_MODE=false)

#### Pre-Agentic Features
- [x] Full 8-step sequential pipeline with real web scraping
- [x] Real-time activity log via WebSockets
- [x] Abort job functionality
- [x] Jobs dashboard with status tracking
- [x] Cache viewer for debugging
- [x] Results page with thesis display
- [x] Excel download functionality
- [x] Admin page for sector knowledge files
- [x] Current market price fetching via yfinance
- [x] PDF extraction from investor presentations, annual reports, concall transcripts

### Excel Model Structure (8+ Sheets)
1. **Cover** - Company summary and recommendation
2. **P&L** - Historical + 5-year projections with formulas
3. **Balance Sheet** - Historical + 5-year projections
4. **ROE Tree** - DuPont analysis (NPM × Asset Turnover × Equity Multiplier)
5. **Quarterly** - Last 12 quarters of results
6. **Key Ratios** - Historical financial ratios
7. **Valuation** - RIV model with editable assumptions
8. **Thesis** - Full investment note
9. **Peer Comparison** - Sector peer metrics (created if data available)

Note: Empty sheets (like Assumptions) are now automatically skipped to produce cleaner output.

## API Endpoints
- `POST /api/generate/` - Create new job
- `GET /api/generate/jobs/` - List all jobs
- `GET /api/generate/progress/{job_id}` - Get job progress
- `GET /api/generate/result/{job_id}` - Get job result
- `GET /api/generate/download/{job_id}` - Download Excel file
- `POST /api/generate/retry/{job_id}` - Retry failed job
- `POST /api/generate/abort/{job_id}` - Abort running job
- `GET /api/generate/cache/{ticker}` - View cached data
- `DELETE /api/generate/cache/{ticker}` - Clear cache
- `GET /api/admin/knowledge-files` - List knowledge files
- `GET /api/admin/knowledge-files/{filename}` - Get knowledge file content
- `PUT /api/admin/knowledge-files/{filename}` - Update knowledge file
- `GET /api/admin/knowledge-gaps` - View flagged knowledge gaps

## Remaining Tasks (Prioritized Backlog)

### P1 - High Priority
- [ ] Fix empty "Assumptions" sheet in Excel (data format mismatch - agent stores free-form text, Excel expects numeric arrays)
- [ ] Improve market_cap fetching (sometimes returns None from Yahoo Finance)

### P2 - Medium Priority  
- [ ] Export thesis to PDF
- [ ] Historical model comparison
- [ ] More sector knowledge files (Cement, IT, Pharma)
- [ ] Refactor `pipeline_manager.py` to remove legacy sequential pipeline code

### P3 - Low Priority
- [ ] User authentication
- [ ] Multi-ticker batch processing
- [ ] Custom assumption overrides in UI
- [ ] Frontend refactoring with custom hooks
- [ ] Improve WebSocket reliability (race conditions on ProcessingPage)

## Tech Stack
- **Frontend:** React, Tailwind CSS, Shadcn UI, socket.io-client
- **Backend:** FastAPI, Motor (async MongoDB), Uvicorn
- **AI:** Claude claude-sonnet-4-5-20250929 via Emergent LLM Key + LiteLLM
- **Scraping:** Playwright for dynamic content, yfinance for stock prices
- **PDF Parsing:** pdfplumber
- **Excel:** openpyxl

## Key Files
- `backend/services/mosaic_agent.py` - Agentic Claude loop with LiteLLM
- `backend/services/agent_tools.py` - Tool definitions and executor
- `backend/services/pipeline_manager.py` - Pipeline orchestration (agentic + sequential)
- `backend/services/excel_generator.py` - Excel model generation
- `backend/services/pdf_extractor.py` - PDF download and parsing
- `backend/services/scraper_service.py` - Web scraping + price fetching
- `backend/services/claude_service.py` - AI integration (sequential mode)
- `backend/services/cache_service.py` - Step data caching

## Frontend Pages
- `frontend/src/pages/Landing.jsx` - Redesigned landing page
- `frontend/src/pages/Processing.jsx` - Redesigned processing page with tool display
- `frontend/src/pages/Results.jsx` - Redesigned results page with thesis tabs

## Environment Variables
- `MOSAIC_AGENTIC_MODE=true` - Enable agentic mode (default: true)
- `EMERGENT_LLM_KEY` - Emergent Universal Key for Claude API
- `MONGO_URL` - MongoDB connection string
- `DB_NAME` - Database name
