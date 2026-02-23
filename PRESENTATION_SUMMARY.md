# Mosaic - Presentation Summary

## One-Liner
**Mosaic is an autonomous AI system that converts a stock ticker into a professional Excel financial model in under 4 minutes.**

---

## The Problem
Investment analysts spend 4-8 hours manually:
- Collecting financial data from multiple sources
- Building Excel models with formulas
- Writing investment theses

## The Solution
Mosaic automates the entire workflow:
```
Input: "HDFCBANK" → Output: Complete Excel Model + Investment Thesis
```

---

## Pipeline Visualization

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           MOSAIC PIPELINE (3-4 minutes)                        │
└────────────────────────────────────────────────────────────────────────────────┘

USER INPUT                    PROCESSING                         OUTPUT
    │                             │                                 │
    ▼                             │                                 │
┌─────────┐                       │                                 │
│ Ticker  │                       │                                 │
│HDFCBANK │                       │                                 │
└────┬────┘                       │                                 │
     │                            │                                 │
     ▼                            │                                 │
┌─────────────────────────────────┴─────────────────────────────────┐
│                                                                    │
│  STEP 1: Company ID          [5-8 sec]                            │
│  ├── Playwright → Screener.in (company name, sector)              │
│  ├── Yahoo Finance API → Current price (₹1,823.45)                │
│  └── Claude AI → Classify as "Bank" → Use banks.md                │
│                                                                    │
│  STEP 2: Annual Financials   [8-12 sec]                           │
│  ├── Playwright → Screener.in P&L section                         │
│  ├── BeautifulSoup → Parse 12 years of data                       │
│  └── Extract: Revenue, Expenses, Net Profit, EPS                  │
│                                                                    │
│  STEP 3: Quarterly Results   [5-8 sec]                            │
│  └── Playwright → Last 12 quarters data                           │
│                                                                    │
│  STEP 4: PDF Analysis        [60-90 sec] ⭐ Most Complex          │
│  ├── Download 2 Investor Presentations (PPT PDFs)                 │
│  │   └── Claude AI → Extract: NIM 3.8%, CASA 42%, GNPA 1.2%      │
│  ├── Download 1 Annual Report (10-20 MB PDF)                      │
│  │   └── Claude AI → Extract detailed P&L line items              │
│  └── Download 2 Concall Transcripts                               │
│      └── Claude AI → Extract: Management outlook, Analyst Q&A     │
│                                                                    │
│  STEP 5: Assumptions         [10-15 sec]                          │
│  └── Claude AI → Generate 5-year forecast drivers                 │
│      Output: Loan growth 14%→10%, NIM 3.9%→3.8%, etc.            │
│                                                                    │
│  STEP 6: Valuation           [10-12 sec]                          │
│  └── Claude AI → Residual Income Valuation                        │
│      Output: Fair Value ₹2,150, Upside 18%, BUY                  │
│                                                                    │
│  STEP 7: Thesis              [12-15 sec]                          │
│  └── Claude AI → 500-word investment note                         │
│                                                                    │
│  STEP 8: Excel Generation    [3-5 sec]                            │
│  └── openpyxl → 10-sheet workbook with formulas                   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   FINAL OUTPUT         │
                    ├────────────────────────┤
                    │ 📊 Excel Model (10 sheets)
                    │   • P&L (formula-linked)
                    │   • Balance Sheet
                    │   • Valuation
                    │   • ROE Analysis
                    │                        │
                    │ 📝 Investment Thesis   │
                    │   • BUY/HOLD/SELL      │
                    │   • Target Price       │
                    │   • Key Risks          │
                    └────────────────────────┘
```

---

## Key Technologies

| Layer | Technology | Why? |
|-------|------------|------|
| **Frontend** | React + Tailwind | Fast, modern UI |
| **Backend** | FastAPI (Python) | Async processing, easy AI integration |
| **AI** | Claude Sonnet 4.5 | Best reasoning for financial analysis |
| **Scraping** | Playwright | Handles JavaScript-rendered pages |
| **Stock Data** | Yahoo Finance | Reliable, free API |
| **PDF Parsing** | pdfplumber | Extracts text from financial PDFs |
| **Excel** | openpyxl | Creates formula-linked workbooks |
| **Real-time** | WebSocket | Live progress updates |
| **Database** | MongoDB | Stores job metadata |

---

## Claude AI Usage (8 calls per job)

| Call # | Purpose | Input | Output |
|--------|---------|-------|--------|
| 1 | Company Classification | Scraped data | Sector, knowledge file |
| 2 | PPT Extraction #1 | PDF text | NIM, CASA, GNPA metrics |
| 3 | PPT Extraction #2 | PDF text | Additional metrics |
| 4 | Annual Report | PDF text | Detailed P&L/BS items |
| 5 | Transcript #1 | PDF text | Management insights |
| 6 | Transcript #2 | PDF text | Analyst concerns |
| 7 | Assumptions | All data | 5-year forecasts |
| 8 | Valuation | Assumptions | Fair value, recommendation |
| 9 | Thesis | Everything | Investment note |

**Total AI Cost:** ~$0.10-0.15 per job

---

## Sample Output Metrics

For UNIONBANK job completed in 3 minutes 12 seconds:

| Metric | Value |
|--------|-------|
| Current Price | ₹193.98 |
| Target Price | ₹216 |
| Upside | +11.1% |
| Recommendation | BUY |
| Excel Sheets | 10 |
| Historical Years | 12 |
| Forecast Years | 5 |
| PDF Documents Parsed | 5 |

---

## Innovation Highlights

1. **Autonomous Pipeline** - No human intervention needed
2. **Formula-Linked Excel** - Change assumption → entire model updates
3. **Knowledge Files** - Sector-specific modeling (banks vs. IT)
4. **Real-time Progress** - WebSocket shows live activity log
5. **Caching** - Re-running same ticker uses cached data (instant)

---

## Demo Flow

1. Go to https://stock-analysis-ai-1.preview.emergentagent.com
2. Enter "HDFCBANK" or "UNIONBANK"
3. Watch real-time progress (WebSocket activity log)
4. View results: Recommendation, Thesis, Valuation
5. Download Excel model
6. Open Excel → All sheets have working formulas

---

## Future Scope

- Add more sectors (IT, Pharma, NBFC)
- Parallel PDF processing (2x faster)
- Historical price charts
- Multi-ticker batch processing
- Custom assumption overrides in UI

---

*Mosaic - Built with React, FastAPI, Claude AI, and love for financial analysis*
