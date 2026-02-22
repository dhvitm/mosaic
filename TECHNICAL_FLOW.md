# Mosaic - End-to-End Technical Flow Documentation

## Executive Summary
Mosaic is an autonomous financial modeling system that generates professional-grade Excel models and investment theses for Indian equities. Given a stock ticker, the system scrapes financial data, parses PDF documents, runs AI-powered analysis, and produces a complete financial model in ~3-4 minutes.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                         (React + Tailwind CSS)                              │
│    Landing Page → Processing Page (WebSocket) → Results Page                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Routes    │  │  Pipeline   │  │   Claude    │  │    Excel    │        │
│  │  (REST API) │  │  Manager    │  │   Service   │  │  Generator  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Scraper    │  │    PDF      │  │   Cache     │  │  WebSocket  │        │
│  │  Service    │  │  Extractor  │  │   Service   │  │   Manager   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                    │           │           │           │
                    ▼           ▼           ▼           ▼
        ┌───────────────┐ ┌───────────┐ ┌─────────┐ ┌─────────┐
        │  Screener.in  │ │  Yahoo    │ │  Claude │ │ MongoDB │
        │  (Playwright) │ │  Finance  │ │   API   │ │         │
        └───────────────┘ └───────────┘ └─────────┘ └─────────┘
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | React 18, Tailwind CSS, Shadcn UI | User interface |
| Backend | FastAPI (Python 3.11) | REST API, async processing |
| Database | MongoDB (Motor async driver) | Job metadata storage |
| AI | Claude Sonnet 4.5 (via Emergent LLM Key) | Financial reasoning, data extraction |
| Web Scraping | Playwright (headless Chromium) | Dynamic page scraping |
| Stock Prices | Yahoo Finance API (yfinance) | Real-time market data |
| PDF Parsing | pdfplumber | Text extraction from PDFs |
| Excel | openpyxl | Financial model generation |
| Real-time Updates | WebSocket (socket.io) | Live progress streaming |
| Caching | Local filesystem (JSON) | Step result persistence |

---

## End-to-End Flow

### Phase 0: User Input
**Duration: ~1-2 seconds**

```
User enters ticker (e.g., "HDFCBANK") → Frontend validates → Submit
```

1. User types ticker in input field
2. **Debounced validation** (800ms delay) calls:
   ```
   GET /api/generate/validate-ticker/{ticker}
   ```
3. Backend uses Playwright to check if ticker exists on Screener.in
4. Frontend shows ✓ or ✗ based on response
5. User clicks "Generate Model"
6. **POST /api/generate/** creates job in MongoDB

**API Call:**
```json
POST /api/generate/
Request: { "ticker": "HDFCBANK" }
Response: { "id": "uuid", "status": "pending" }
```

---

### Phase 1: Company Identification
**Duration: ~5-8 seconds**

```
Scraper → Screener.in basic data
Yahoo Finance → Current stock price
Claude AI → Metadata classification
```

**What happens:**
1. **Scraper Service** navigates to `https://www.screener.in/company/{ticker}/consolidated/`
2. Extracts company name, sector hints from page
3. **Yahoo Finance API** fetches real-time price:
   ```python
   yf.Ticker(f"{ticker}.NS").info
   # Returns: currentPrice, marketCap, bookValue, PE ratio
   ```
4. **Claude AI** classifies company:
   ```
   Input: Company name, scraped data
   Output: {
     "sector": "Financial Services",
     "industry": "Bank",
     "knowledge_file": "banks.md"
   }
   ```

**Tools Used:**
- Playwright (headless browser)
- yfinance library
- Claude API (claude-sonnet-4-5)

**Cache:** Step result saved to `/app/cached_data/{ticker}/step_1.json`

---

### Phase 2: Annual Financial Data Extraction
**Duration: ~8-12 seconds**

```
Playwright → Screener.in P&L section
Playwright → Screener.in Balance Sheet section
BeautifulSoup → Parse HTML tables
```

**What happens:**
1. Navigate to Screener.in consolidated page
2. Wait for `networkidle` (JavaScript rendering complete)
3. Parse `<section id="profit-loss">` table:
   - Extract 12 years of P&L data
   - Headers: Mar 2014, Mar 2015, ..., Mar 2025
   - Rows: Revenue, Expenses, Net Profit, EPS, etc.
4. Parse `<section id="balance-sheet">` table:
   - Extract 12 years of Balance Sheet data
   - Rows: Equity, Deposits, Advances, Total Assets, etc.
5. Parse `<section id="ratios">` for key ratios

**Data Structure:**
```python
{
  "annual_pnl": {
    "Mar 2024": {
      "Revenue +": 245678,
      "Net Profit +": 45678,
      "EPS in Rs": 85.6
    },
    # ... 11 more years
  },
  "annual_bs": {
    "Mar 2024": {
      "Deposits": 1800000,
      "Advances +": 1500000,
      "Total Assets": 2200000
    }
  }
}
```

**Cache:** `/app/cached_data/{ticker}/step_2.json`

---

### Phase 3: Quarterly Results Extraction
**Duration: ~5-8 seconds**

```
Playwright → Screener.in Quarters section
Parse 12 quarters of data
```

**What happens:**
1. Parse `<section id="quarters">` table
2. Extract last 12 quarters (3 years)
3. Data includes: Revenue, Expenses, Profit, EPS per quarter

**Cache:** `/app/cached_data/{ticker}/step_3.json`

---

### Phase 4: Management Commentary & PDF Analysis
**Duration: ~60-90 seconds** (Most time-consuming step)

This step has multiple sub-phases:

#### 4a. Scrape Screener Commentary (~5s)
```
Screener.in → Pros/Cons, Peer Comparison, Shareholding
```

#### 4b. Scrape Document Links (~5s)
```
Screener.in Documents section → PDF URLs
- Investor Presentations (PPTs)
- Annual Reports
- Concall Transcripts
```

#### 4c. Download & Parse Investor Presentations (~20-30s)
```
For each of 2 presentations:
  1. Download PDF (requests library, ~5s)
  2. Extract text (pdfplumber, ~2s)
  3. AI extraction (Claude API, ~10s)
```

**Claude Prompt for PPT:**
```
Extract key operational metrics from this investor presentation:
- NIM (Net Interest Margin)
- CASA Ratio
- GNPA, NNPA
- ROE, ROA
- Credit Cost
- Key guidance statements

Return as JSON.
```

#### 4d. Download & Parse Annual Reports (~20-30s)
```
For 1 annual report:
  1. Download PDF (~5s, can be 10-20MB)
  2. Extract first 50 pages text (~3s)
  3. AI extraction of detailed P&L and Balance Sheet (~15s)
```

**Claude Prompt for Annual Report:**
```
Extract DETAILED financial line items from this annual report.
For banks, extract:
- Interest on Advances
- Income on Investments
- Interest Expended
- Employee Cost
- Provisions & Contingencies
- etc.

Return as structured JSON matching Excel template.
```

#### 4e. Download & Parse Concall Transcripts (~20-30s)
```
For 2 recent transcripts:
  1. Download PDF (~3s)
  2. Extract text (~2s)
  3. AI extraction of insights (~12s)
```

**Claude Prompt for Transcripts:**
```
Extract key insights from this earnings call:
- Key themes discussed
- Management outlook statements
- Analyst concerns raised
- Specific guidance given

Return as JSON.
```

**Total Claude API Calls in Step 4:** 5 calls
**Cache:** `/app/cached_data/{ticker}/step_4.json` (largest cache file)

---

### Phase 5: Forecast Assumptions Generation
**Duration: ~10-15 seconds**

```
All scraped data + PDF metrics → Claude AI → 5-year forecast assumptions
```

**What happens:**
1. Load knowledge file (`banks.md` or `generic.md`)
2. Combine all data:
   - Historical financials (Step 2)
   - PDF-extracted metrics (Step 4)
   - Peer comparison data
3. Claude generates assumptions:

**Claude Prompt:**
```
Based on the following data for {company}:
- Historical NIM: 3.5%, 3.6%, 3.8%
- Current GNPA: 1.2%
- Management guidance: "Targeting 15% loan growth"
- Sector outlook: [from knowledge file]

Generate 5-year forecast assumptions:
- Loan Growth Rate (FY26-FY30)
- NIM trajectory
- Credit cost assumptions
- etc.

Return as JSON with rationale.
```

**Output:**
```json
{
  "loan_growth_rate": {"FY26": 14, "FY27": 13, "FY28": 12, "FY29": 11, "FY30": 10},
  "nim": {"FY26": 3.9, "FY27": 4.0, "FY28": 4.0, "FY29": 3.9, "FY30": 3.8},
  "credit_cost": {"FY26": 0.8, "FY27": 0.7, "FY28": 0.6, "FY29": 0.5, "FY30": 0.5},
  "rationale": "..."
}
```

**Cache:** `/app/cached_data/{ticker}/step_5.json`

---

### Phase 6: Valuation
**Duration: ~10-12 seconds**

```
Assumptions + Historical data → Claude AI → Fair Value calculation
```

**What happens:**
1. For banks: Residual Income Valuation (RIV)
   - Cannot use DCF (banks don't have traditional FCF)
   - Value = Book Value + PV(Residual Income)
   - Residual Income = (ROE - Cost of Equity) × Book Value

2. Claude calculates:
   - Cost of Equity (typically 12-14% for Indian banks)
   - Terminal growth rate (3-4%)
   - Fair value per share
   - Recommendation (BUY/HOLD/SELL based on upside)

**Output:**
```json
{
  "cost_of_equity": 13.0,
  "terminal_growth": 4.0,
  "fair_value": 215.5,
  "current_price": 193.98,
  "upside_percent": 11.1,
  "recommendation": "BUY",
  "rationale": "ROE of 17.5% exceeds CoE of 13%..."
}
```

**Cache:** `/app/cached_data/{ticker}/step_6.json`

---

### Phase 7: Investment Thesis Generation
**Duration: ~12-15 seconds**

```
All data + Valuation → Claude AI → Professional thesis
```

**Claude Prompt:**
```
Write a detailed investment thesis for {company}.

KEY DATA:
- Current Price: ₹193.98
- Target Price: ₹216
- Recommendation: BUY
- Key Metrics: NIM 3.8%, GNPA 1.2%, ROE 17.5%

CONCALL INSIGHTS:
- Management expects 15% loan growth
- Focus on retail portfolio

Write 4-6 paragraphs covering:
1. Recommendation Summary
2. Investment Case (3-4 bullet points)
3. Key Risks
4. Valuation methodology

Keep under 500 words. Professional tone.
```

**Output:** 400-500 word investment note

**Cache:** `/app/cached_data/{ticker}/step_7.json`

---

### Phase 8: Excel Model Generation
**Duration: ~3-5 seconds**

```
All data → openpyxl → Multi-sheet Excel workbook
```

**What happens:**
1. Create workbook with 10 sheets:

| Sheet | Content | Data Source |
|-------|---------|-------------|
| Cover | Summary, Recommendation | Step 6, 7 |
| Assumptions | Forecast drivers (editable) | Step 5 |
| P&L | 5yr historical + 5yr forecast | Step 2, 4, formulas |
| Balance Sheet | 5yr historical + 5yr forecast | Step 2, 4, formulas |
| ROE Tree | DuPont analysis | Linked to P&L, BS |
| Quarterly | Last 12 quarters | Step 3 |
| Key Ratios | NIM, CASA, NPA trends | Calculated |
| Valuation | RIV model with formulas | Step 6 |
| Peer Comparison | Sector peers | Step 4 |
| Thesis | Full investment note | Step 7 |

2. **Key Feature:** All sheets are formula-linked
   - Change an assumption → P&L updates → Valuation updates
   - Example: `=P&L!G23` references Net Profit from P&L sheet

3. Formatting:
   - Green cells = Forecast (editable)
   - Blue cells = Linked from other sheets
   - Headers styled with borders

**Output:** `/app/generated_models/{ticker}_model_{timestamp}.xlsx`

---

## Timeline Summary

| Step | Description | Duration | Key Tools |
|------|-------------|----------|-----------|
| 0 | User Input & Validation | 1-2s | Playwright |
| 1 | Company Identification | 5-8s | Playwright, yfinance, Claude |
| 2 | Annual Financials | 8-12s | Playwright, BeautifulSoup |
| 3 | Quarterly Results | 5-8s | Playwright, BeautifulSoup |
| 4 | Management Commentary | 60-90s | Playwright, pdfplumber, Claude (5 calls) |
| 5 | Assumptions | 10-15s | Claude |
| 6 | Valuation | 10-12s | Claude |
| 7 | Thesis | 12-15s | Claude |
| 8 | Excel Generation | 3-5s | openpyxl |
| **Total** | | **~3-4 minutes** | |

---

## Real-Time Progress Updates

Throughout the pipeline, WebSocket messages are sent to the frontend:

```javascript
// WebSocket connection
ws://backend/api/generate/ws/{job_id}

// Message types
{
  "type": "step_update",
  "step": 4,
  "status": "processing",
  "message": "Parsing 2 investor presentation PDFs..."
}

{
  "type": "activity",
  "category": "data_processing",
  "message": "Extracted NIM: 3.8%, CASA: 42%, GNPA: 1.2%"
}
```

---

## Caching Strategy

**Purpose:** Avoid redundant scraping and API calls for the same ticker

**Structure:**
```
/app/cached_data/
├── HDFCBANK/
│   ├── step_1.json  (5 KB)
│   ├── step_2.json  (50 KB)
│   ├── step_3.json  (20 KB)
│   ├── step_4.json  (200 KB)  ← Largest (PDF data)
│   ├── step_5.json  (10 KB)
│   ├── step_6.json  (5 KB)
│   └── step_7.json  (8 KB)
├── ICICIBANK/
│   └── ...
```

**Cache Hit Logic:**
```python
cached_data = CacheService.load_step_data(ticker, step_number)
if cached_data and is_valid(cached_data):
    return cached_data  # Skip entire step
else:
    # Execute step, then cache
    result = await execute_step()
    CacheService.save_step_data(ticker, step_number, result)
```

**Cache Invalidation:** Manual via `/api/generate/cache/{ticker}` DELETE

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Ticker not found | Return 404, show error on frontend |
| Screener.in timeout | Retry 3 times with exponential backoff |
| PDF download failed | Skip that PDF, continue with others |
| Claude API error | Retry once, then use fallback assumptions |
| Large PDF (>15MB) | Skip to avoid memory issues |
| Job takes too long | User can "Abort" job |

---

## Cost Analysis

| Resource | Cost per Job |
|----------|-------------|
| Claude API (8 calls) | ~$0.10-0.15 |
| Compute (3-4 min) | Included in hosting |
| Storage (cache) | ~300 KB per ticker |

---

## Security Considerations

1. **No user authentication** (prototype stage)
2. **Admin panel** password-protected (basic auth)
3. **API keys** stored in environment variables
4. **Rate limiting** on Screener.in (2s delays between requests)

---

## Potential Improvements

1. **Parallel PDF processing** - Download all PDFs concurrently
2. **Incremental updates** - Only re-run steps with stale data
3. **More sectors** - Add NBFC, IT, Pharma knowledge files
4. **Historical price charts** - Add to Results page
5. **PDF caching** - Store downloaded PDFs to avoid re-downloading

---

## Appendix: API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/generate/ | Create new job |
| GET | /api/generate/jobs/ | List all jobs |
| GET | /api/generate/progress/{job_id} | Get job progress |
| GET | /api/generate/result/{job_id} | Get completed result |
| GET | /api/generate/download/{job_id} | Download Excel file |
| POST | /api/generate/abort/{job_id} | Abort running job |
| POST | /api/generate/retry/{job_id} | Retry failed job |
| GET | /api/generate/validate-ticker/{ticker} | Validate ticker |
| GET | /api/admin/knowledge-files | List knowledge files |
| PUT | /api/admin/knowledge-files/{filename} | Update knowledge file |

---

*Document generated for academic presentation - Mosaic Financial Model Generator*
