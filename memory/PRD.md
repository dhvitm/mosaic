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
- **Pipeline Manager:** 8-step async pipeline
- **Scraper Service:** Playwright-based scraping from Screener.in + current market price fetching
- **PDF Extractor:** Downloads and parses investor presentations, annual reports, and concall transcripts
- **Claude AI Integration:** For assumptions, valuation, and thesis generation
- **Excel Generator:** openpyxl-based model with formulas and detailed AR data mapping
- **Cache Service:** Local file caching for step results (all parsed insights cached)
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
1. **Company Identification:** Scrape company metadata + fetch current market price from Screener.in
2. **Annual Financials:** Scrape P&L and Balance Sheet (12 years)
3. **Quarterly Results:** Scrape quarterly data (12 quarters)
4. **Management Commentary + PDF Extraction:** 
   - Scrape pros/cons, peers from Screener.in
   - Download 3 investor presentation PDFs and extract key metrics
   - Download 2 annual reports and extract detailed P&L/BS line items
   - Download last 4 quarters of concall transcripts and extract insights
5. **Assumptions Generation:** Claude AI generates forecasts using PDF-extracted metrics
6. **Valuation:** RIV model linked to projected financials with current market price comparison
7. **Thesis Generation:** Claude AI writes thesis using metrics from PDFs and concall insights
8. **Excel Generation:** Build mechanically-linked model with detailed AR data

## What's Been Implemented

### Completed Features
- [x] Full 8-step pipeline with real web scraping
- [x] Real-time activity log via WebSockets
- [x] Abort job functionality
- [x] Jobs dashboard with status tracking
- [x] Cache viewer for debugging
- [x] Results page with thesis display
- [x] Excel download functionality

### Latest Updates (Dec 2025)

#### 1. Enhanced Excel Data from Annual Reports (P0)
- Fixed `excel_generator.py` to properly map detailed P&L and Balance Sheet line items
- Added year matching logic to overlay AR data on correct historical columns
- New line items populated: Employee Cost, Provisions, Interest on Deposits, CASA Deposits, etc.
- All data sources: Screener.in (basic) + Annual Reports (detailed) merged intelligently

#### 2. Concall Transcript Parsing (P1)
- Added `process_concall_transcripts()` in `pdf_extractor.py`
- Extracts from last 4 quarters:
  - Key themes
  - Management outlook
  - Analyst concerns
  - Guidance statements
- Insights integrated into thesis generation

#### 3. Current Market Price Fetching (P1)
- Added `get_current_market_price()` in `scraper_service.py`
- Fetches real-time price from Screener.in during Step 1
- Used in valuation sheet for upside/downside calculation
- Price timestamp stored for reference

#### 4. Caching of All Parsed Insights
Step 4 now caches:
- `detailed_pnl` - from annual reports
- `detailed_bs` - from annual reports
- `transcript_insights` - full transcript data
- `concall_themes` - key discussion themes
- `analyst_concerns` - questions/concerns raised
- `management_outlook` - forward guidance
- `management_guidance` - specific targets

### Excel Model Structure (10 Sheets)
1. **Cover** - Company summary and recommendation
2. **Assumptions** - Editable forecast drivers (yellow cells)
3. **P&L** - Historical + 5-year projections with detailed line items
4. **Balance Sheet** - Historical + 5-year projections with CASA, etc.
5. **ROE Tree** - DuPont analysis with cross-sheet links
6. **Quarterly** - Last 12 quarters of results
7. **Key Ratios** - Historical financial ratios
8. **Valuation** - RIV model linked to projections + current market price
9. **Peer Comparison** - Sector peer metrics
10. **Thesis** - Full investment note

### Data Flow
```
Screener.in → P&L, BS, Quarterly, Pros/Cons, Peers, Current Price
    ↓
Screener Documents → PPT Links, AR Links, Transcript Links
    ↓
PDF Download → Extract Text (pdfplumber)
    ↓
Claude AI → Extract Metrics (NIM, CASA, GNPA) + Detailed Financials + Transcript Insights
    ↓
Step 4 Cache → All insights stored for reuse
    ↓
Step 5 → Use metrics for Assumptions
    ↓
Step 7 → Use metrics + concall insights in Thesis
    ↓
Excel → All formulas linked, AR data overlaid, projections included
```

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

### P2 - Medium Priority
- [ ] Admin page for editing .md knowledge files (backend ready, frontend needed)
- [ ] Export thesis to PDF
- [ ] Historical model comparison

### P3 - Low Priority
- [ ] User authentication
- [ ] Multi-ticker batch processing
- [ ] Custom assumption overrides in UI
- [ ] More sector knowledge files (Cement, IT, Pharma)
- [ ] Frontend refactoring with custom hooks

## Tech Stack
- **Frontend:** React, Tailwind CSS, Shadcn UI, socket.io-client
- **Backend:** FastAPI, Motor (async MongoDB), Uvicorn
- **AI:** Claude claude-sonnet-4-5 via Emergent LLM Key
- **Scraping:** Playwright for dynamic content
- **PDF Parsing:** pdfplumber
- **Excel:** openpyxl

## Key Files
- `backend/services/excel_generator.py` - Excel model with AR data mapping
- `backend/services/pdf_extractor.py` - PDF download, metric extraction, transcript parsing
- `backend/services/scraper_service.py` - Web scraping + current price fetching
- `backend/services/pipeline_manager.py` - Pipeline orchestration
- `backend/services/claude_service.py` - AI integration
- `backend/services/cache_service.py` - Step data caching
- `frontend/src/pages/Landing.jsx` - Main landing page
