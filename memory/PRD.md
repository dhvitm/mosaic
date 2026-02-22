# Mosaic - Financial Model Generator for Indian Equities

## Product Overview
Mosaic is a professional-grade financial model generator for Indian stock market analysis. It takes an NSE/BSE ticker as input and produces:
1. A fully-linked Excel financial model (.xlsx) with historical data and 5-year projections
2. A detailed AI-generated investment thesis with actual metrics from investor presentations

## Core Requirements
- **Input:** Single NSE/BSE stock ticker
- **Output:** 
  - Excel model with P&L, Balance Sheet, ROE Tree, Valuation (all formula-driven)
  - Investment thesis with recommendation and target price, citing actual metrics

## Technical Architecture

### Backend (FastAPI)
- **Pipeline Manager:** 8-step async pipeline
- **Scraper Service:** Playwright-based scraping from Screener.in
- **PDF Extractor:** Downloads and parses investor presentation PDFs
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
4. **Management Commentary + PDF Extraction:** 
   - Scrape pros/cons, peers from Screener.in
   - Download 3 investor presentation PDFs
   - Extract key metrics (NIM, CASA, GNPA, ROE, etc.) using AI
5. **Assumptions Generation:** Claude AI generates forecasts using PDF-extracted metrics
6. **Valuation:** RIV model linked to projected financials
7. **Thesis Generation:** Claude AI writes thesis using actual metrics from PDFs
8. **Excel Generation:** Build mechanically-linked model

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

#### 1. PDF Extraction from Investor Presentations
- Downloads up to 3 quarterly investor presentation PDFs
- Extracts key banking metrics using AI:
  - NIM (Net Interest Margin): 3.35%
  - CASA Ratio: 34%
  - GNPA: 1.24%
  - NNPA: 0.4%
  - ROE: 13.9%
  - ROA: 1.92%
  - CAR: 19.9%
  - Cost-to-Income: 39.2%
  - Loan Growth: 11.9%
  - Deposit Growth: 11.6%
- Extracts management guidance statements
- Extracts 14+ operational highlights with actual numbers

#### 2. Formula-Driven Valuation Sheet
- Complete RIV model with formulas:
  - Net Profit linked to P&L (`='P&L'!G19`)
  - Equity linked to Balance Sheet (`='Balance Sheet'!G8`)
  - Residual Income = PAT - Required Return
  - Terminal Value with growth formula
  - Fair Value = (Book Value + Sum PV of RI + Terminal Value) / Shares

#### 3. ROE Tree (DuPont Analysis)
- ROE = NPM × Asset Turnover × Equity Multiplier
- Cross-sheet references to P&L and Balance Sheet

#### 4. 5-Year Projections (FY26E-FY30E)
- All P&L and BS items with growth formulas
- Linked to editable Assumptions sheet

### Excel Model Structure (10 Sheets)
1. **Cover** - Company summary and recommendation
2. **Assumptions** - Editable forecast drivers (yellow cells)
3. **P&L** - Historical + 5-year projections with formulas
4. **Balance Sheet** - Historical + 5-year projections
5. **ROE Tree** - DuPont analysis with cross-sheet links
6. **Quarterly** - Last 12 quarters of results
7. **Key Ratios** - Historical financial ratios
8. **Valuation** - RIV model linked to projections
9. **Peer Comparison** - Sector peer metrics
10. **Thesis** - Full investment note

### Data Flow
```
Screener.in → P&L, BS, Quarterly, Pros/Cons, Peers
    ↓
Screener Documents → PPT Links (15+)
    ↓
PDF Download → Extract Text (pdfplumber)
    ↓
Claude AI → Extract Metrics (NIM, CASA, GNPA, etc.)
    ↓
Step 5 → Use metrics for Assumptions
    ↓
Step 7 → Use metrics in Thesis (with actual numbers)
    ↓
Excel → All formulas linked, projections included
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

### P1 - High Priority
- [ ] Parse concall transcripts (currently have links but not parsing)
- [ ] Add more sector-specific knowledge files (Cement, IT, Pharma)
- [ ] Handle non-PDF presentation formats

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
- **PDF Parsing:** pdfplumber
- **Excel:** openpyxl

## Key Files
- `backend/services/pdf_extractor.py` - **NEW** PDF download and metric extraction
- `backend/services/excel_generator.py` - Excel model with formula-driven valuation
- `backend/services/scraper_service.py` - Web scraping from Screener.in
- `backend/services/pipeline_manager.py` - Pipeline orchestration
- `backend/services/claude_service.py` - AI integration
- `frontend/src/pages/Results.jsx` - Results display page
