# Mosaic - Financial Model Generator for Indian Equities

## Product Overview
Mosaic is a professional-grade financial model generator for Indian stock market analysis. It takes an NSE/BSE ticker as input and produces:
1. A fully-linked Excel financial model (.xlsx) with historical data and 5-year projections
2. A detailed AI-generated investment thesis

## Core Requirements
- **Input:** Single NSE/BSE stock ticker
- **Output:** 
  - Excel model with P&L, Balance Sheet, ROE Tree, Valuation, and forecasts
  - Investment thesis with recommendation (BUY/HOLD/SELL) and target price

## Technical Architecture

### Backend (FastAPI)
- **Pipeline Manager:** 8-step async pipeline
- **Scraper Service:** Playwright-based scraping from Screener.in
- **Claude AI Integration:** For assumptions, valuation, and thesis generation
- **Excel Generator:** openpyxl-based model with formulas
- **Cache Service:** Local file caching for step results
- **WebSocket Manager:** Real-time progress updates

### Frontend (React)
- **Landing Page:** Ticker input
- **Processing Page:** Live activity log via WebSockets
- **Results Page:** Thesis display with Excel download
- **Jobs Page:** Dashboard for all jobs
- **Cache Viewer:** View cached data per ticker

### Database (MongoDB)
- Jobs collection for job metadata

## Pipeline Steps
1. **Company Identification:** Scrape company metadata from Screener.in
2. **Annual Financials:** Scrape P&L and Balance Sheet (12 years)
3. **Quarterly Results:** Scrape quarterly data (12 quarters)
4. **Management Commentary:** Scrape pros/cons, peers, investor presentations from Screener.in Documents
5. **Assumptions Generation:** Claude AI generates forecast assumptions
6. **Valuation:** RIV model, peer comparisons, target price
7. **Thesis Generation:** Claude AI writes investment note
8. **Excel Generation:** Build mechanically-linked model with formulas

## What's Been Implemented (Feb 22, 2026)

### Completed Features
- [x] Full 8-step pipeline with real web scraping
- [x] Real-time activity log via WebSockets
- [x] Abort job functionality
- [x] Jobs dashboard with status tracking
- [x] Cache viewer for debugging
- [x] Results page with thesis display
- [x] Excel download functionality

### Latest Enhancements (This Session)
- [x] **Excel with Mechanical Linking:** All calculations use formulas (e.g., PBT = Total Income - Total Expenses)
- [x] **5-Year Projections:** FY26E-FY30E columns with growth formulas linked to Assumptions sheet
- [x] **ROE Tree (DuPont Analysis):** New sheet decomposing ROE into NPM × Asset Turnover × Equity Multiplier
- [x] **Cross-sheet References:** ROE Tree links to P&L and Balance Sheet for real mechanical linking
- [x] **Screener.in Documents Scraping:** Replaced BSE scraping with Screener.in Documents section scraping
- [x] **Investor Presentations Extraction:** Now scrapes 15+ PPT links with quarter information

### Excel Model Structure (10 Sheets)
1. Cover - Company summary and recommendation
2. Assumptions - Editable forecast drivers (yellow cells)
3. P&L - Historical + 5-year projections with formulas
4. Balance Sheet - Historical + 5-year projections
5. ROE Tree - DuPont analysis with cross-sheet links
6. Quarterly - Last 12 quarters of results
7. Key Ratios - Historical financial ratios
8. Valuation - RIV model with target price
9. Peer Comparison - Sector peer metrics
10. Thesis - Full investment note

### Excel Formula Examples
- `Total Income = Revenue + Interest + Other Income`
- `PBT = Total Income - Total Expenses`
- `Net Profit = PBT - Tax`
- `ROE = PAT / Average Equity`
- `Asset Turnover = Revenue / Average Assets`

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

## Remaining Tasks (Backlog)

### P1 - High Priority
- [ ] Parse and summarize concall transcripts with AI
- [ ] Extract operational metrics from investor presentations
- [ ] Add more sector-specific knowledge files (Cement, IT, Pharma)

### P2 - Medium Priority
- [ ] Admin page for editing .md knowledge files
- [ ] Export thesis to PDF
- [ ] Historical model comparison

### P3 - Low Priority
- [ ] User authentication
- [ ] Multi-ticker batch processing
- [ ] Custom assumption overrides in UI

## Tech Stack
- **Frontend:** React, Tailwind CSS, Shadcn UI, socket.io-client
- **Backend:** FastAPI, Motor (async MongoDB), Uvicorn
- **AI:** Claude claude-sonnet-4-5 via Emergent LLM Key
- **Scraping:** Playwright for dynamic content
- **Excel:** openpyxl

## Key Files
- `backend/services/excel_generator.py` - Excel model generation with formulas
- `backend/services/scraper_service.py` - Web scraping from Screener.in
- `backend/services/pipeline_manager.py` - Pipeline orchestration
- `backend/services/claude_service.py` - AI integration
- `frontend/src/pages/Results.jsx` - Results display page
