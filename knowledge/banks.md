# SECTOR: BANKS
# Applies to: Scheduled Commercial Banks (Private and Public Sector)
# Does NOT apply to: NBFCs, HFCs, MFIs (these need separate templates)

## SECTOR CLASSIFICATION SIGNALS
A company should be routed to this template if Screener.in shows:
- Industry contains "Bank" or "Banking"
- The company has "Bank" in its name
- Balance sheet shows Deposits as a liability line item
- Revenue line is "Interest Earned" not "Revenue from Operations"

## WHAT DRIVES A BANK'S EARNINGS

A bank makes money on the spread between what it earns on assets 
(advances and investments) and what it pays on liabilities (deposits 
and borrowings). The key causal chain is:

REVENUE SIDE:
- Loan book size × Yield on advances = Interest on advances
- Investment book size × Yield on investments = Interest on investments  
- Yield on advances is driven by: segment mix (retail yields higher than 
  corporate), repo rate (most advances are floating rate, linked to repo 
  via MCLR or repo-linked), and competitive dynamics
- Non-interest income (fees, forex, treasury) is typically modeled as 
  a % of total interest income

COST SIDE:
- Deposits × Cost of deposits = Interest expended (majority)
- Cost of deposits is driven by: CASA ratio (current and savings accounts 
  are cheap — CA is zero cost, SA is ~2-3%), term deposit cost (market 
  rate, reprices with repo rate changes but with a lag), and the bank's 
  franchise strength
- CASA ratio is the single most important structural advantage a bank 
  can have — higher CASA = lower cost of funds = better NIM

NIM (Net Interest Margin) = (Interest earned - Interest expended) / 
Average Interest Earning Assets
This is the most watched metric for any bank. Indian private banks 
typically have NIMs of 3-5%.

OPERATING LEVERAGE:
- OpEx is relatively fixed in the short term (branch network, staff)
- C/I ratio (Cost to Income) improves as revenue grows faster than costs
- Target C/I for efficient Indian private banks is 40-50%

ASSET QUALITY:
- GNPA ratio = Gross Non-Performing Assets / Total Advances
- PCR (Provision Coverage Ratio) = Provisions held / Gross NPA
- Credit cost = Provisions made in a year / Average advances
- Asset quality varies significantly by segment — MFI and unsecured 
  retail are higher risk, secured retail (housing, gold) and large 
  corporate are lower risk

CAPITAL:
- Banks are regulated — must maintain minimum CRAR (Capital to Risk 
  Weighted Assets Ratio) of 11.5% under RBI norms
- Equity raises are common when loan growth is aggressive

## DATA SOURCES AND WHAT TO EXTRACT

### SOURCE 1: SCREENER.IN
URL: https://www.screener.in/company/{TICKER}/consolidated/

Extract from the main page:
- Current market price
- Market capitalization  
- Shares outstanding
- P/E ratio, P/B ratio
- Dividend yield
- From the financial tables: last 10 years of annual P&L and BS

Key P&L line items to extract:
- Interest Earned (total)
- Interest on Advances
- Income on Investments  
- Interest on Balances with RBI
- Other Interest Income
- Other Income (non-interest)
- Total Income
- Interest Expended
- Operating Expenses (Staff + Other)
- Provisions and Contingencies
- Profit Before Tax
- Tax
- PAT
- Minority Interest
- Consolidated PAT

Key BS line items to extract:
ASSETS:
- Cash and Balances with RBI
- Balances with Banks and Money at Call
- Investments
- Advances (Net)
- Fixed Assets
- Other Assets
- Total Assets

LIABILITIES:
- Capital (paid-up equity)
- Reserves and Surplus
- Minority Interest
- Deposits
- Borrowings
- Other Liabilities and Provisions
- Total Liabilities

Also extract quarterly results for last 12 quarters:
- NII, Other Income, Operating Expenses, Provisions, PAT

### SOURCE 2: BSE INVESTOR PRESENTATIONS
URL pattern: Search BSE filings for the company, filter by 
"Investor Presentations" category
Alternative: Company IR page, typically at 
{companyname}.com/investor-relations

For each of the last 8 quarterly presentations, extract:

ADVANCES BREAKDOWN (segment-wise, in ₹ Cr):
- Retail sub-segments: Housing, LAP (Loan Against Property), Auto, 
  Personal Loans, Credit Cards, Other Retail
- Gold Loans
- Business Banking (BuB) / SME
- Agriculture
- Commercial Vehicle / Construction Equipment (CV/CE)
- Microfinance (MFI) — if applicable
- Corporate / CIB (Corporate and Institutional Banking)
- Commercial Banking (CoB) — if applicable
Note: Segment names vary by bank. Extract whatever segments are 
disclosed and map to the closest category above.

DEPOSIT BREAKDOWN:
- Current Account balance
- Savings Account balance
- Total CASA
- CASA ratio (%)
- Term Deposits
- Total Deposits

YIELDS AND COSTS:
- Yield on Advances (%)
- Yield on Investments (%)
- Cost of Deposits (%)
- Cost of Funds (%)
- NIM on assets (%)
- NIM on IEAs — Interest Earning Assets (%)

ASSET QUALITY (segment-wise where disclosed):
- Gross NPA by segment (₹ Cr)
- Total Gross NPA (₹ Cr and %)
- Net NPA (₹ Cr and %)
- Provision Coverage Ratio (%)
- Slippage ratio (%)
- Credit cost (%)

OTHER:
- Cost-to-Income ratio (%)
- ROA (%)
- ROE (%)
- CRAR / Capital Adequacy Ratio (%)
- Tier 1 ratio (%)
- CD ratio (%)
- Number of branches, ATMs (for context)

### SOURCE 3: CONCALL TRANSCRIPTS
Search BSE filings for "Earnings Call" or "Concall" transcripts.
Alternative sources: Screener.in concall section, 
Trendlyne.com, company IR page.

Extract last 4 quarters of concall transcripts.

From each transcript, extract:
- All management guidance on NIM (range, direction)
- Loan growth guidance (absolute or as GDP multiple)
- Credit cost guidance (range for the year)
- CASA ratio target
- ROA / ROE targets management has stated
- Any segment-specific commentary (e.g. "reducing MFI exposure")
- Dividend policy statements
- Capital adequacy and equity raise commentary
- Any regulatory or macro risks flagged by management
- Key analyst questions and management responses on outlook

### SOURCE 4: ANNUAL REPORT (most recent only)
Do NOT download and process the full annual report — they are 
300-500 pages and most is irrelevant.

Instead, look for the standalone filing on BSE. Extract only:
- Consolidated Profit & Loss Account
- Consolidated Balance Sheet  
- Schedule 9: Advances (for segment breakdown)
- Schedule 4: Borrowings (for borrowing mix)
- Capital Adequacy disclosures (Basel III)
- MD&A section (Chairman/MD letter and business review)
- Notes on provisions and contingent liabilities

## WORKBOOK STRUCTURE

Build an Excel workbook with the following sheets in this order:

### Sheet 1: Cover
- Company name, ticker, current date
- Analyst name field (leave blank)
- Recommendation and target price (populated after valuation)
- Brief one-paragraph thesis summary

### Sheet 2: PnL (Profit & Loss)
Rows (years: FY21 through FY[current+5]):
INCOME:
- Interest Earned (sum of below)
  - Interest on Advances [= avg advances × yield on advances]
  - Income on Investments [= avg investments × yield on investments]  
  - Interest on Balances with RBI [= RBI balance × short rate]
  - Other Interest Income [= prior year × growth assumption]
- Other Income [= total interest earned × other income ratio]
- Total Income

EXPENDITURE:
- Interest Expended [built from deposit schedule]
- Operating Expenses [= advances × opex/advances ratio]
- Provisions and Contingencies (sum of below)
  - Provisions towards NPAs [from GNPA schedule]
  - Taxation [= PBT × tax rate]
  - Other Provisions [= residual]
- Total Expenditure

- PAT [= Total Income - Interest Expended - OpEx - NPA Provisions 
       - Other Provisions - Tax]
- Minority Interest adjustment
- Balance Brought Forward
- Amount Available for Appropriation
- Appropriations (statutory reserve, revenue reserve, dividends etc.)
- Retained Earnings

Historical years: hardcoded from Screener + annual report data
Forecast years: formula-driven from Assumptions sheet

### Sheet 3: BS (Balance Sheet)
Rows (same year range):
ASSETS:
- Cash and Balances with RBI [= deposits × CRR%]
- Balances with Banks and Money at Call [= deposits × call money %]
- Investments [= NDTL × investment ratio]
- Advances [from Advances Build sheet]
- Fixed Assets [= prior year × (1 + growth rate)]
- Other Assets [= advances × other assets ratio]
- Total Assets

LIABILITIES:
- Capital [= constant unless equity raise]
- Reserves and Surplus [= prior year + PAT - dividends + other]
- Minority Interest [= prior year × growth rate]
- Deposits [from Deposit Schedule]
- Borrowings [= PLUG: Total Assets - all other liabilities]
- Other Liabilities [= deposits × other liabilities ratio]
- Total Liabilities and Equity

- Balance Check row [= Total Assets - Total Liabilities, must be 0]
- Equity Raise row [explicit assumption]

### Sheet 4: Assumptions
Single source of truth for ALL forecast drivers.
Layout: rows are assumption parameters, columns are forecast years.

GROUP 1 — MACRO:
- Nominal GDP Growth Rate
- Repo Rate (year-end)
- Change in Repo Rate

GROUP 2 — LOAN GROWTH:
- Loan Growth Multiple of GDP
- Loan Growth Rate [= GDP growth × multiple]

GROUP 3 — DEPOSIT MIX:
- CASA Ratio
- CA Ratio (within CASA)
- SA Ratio (within CASA)
- Term Deposit Ratio [= 1 - CASA]
- Credit-Deposit Ratio

GROUP 4 — RATES:
- Rate Transmission on Advances (% of repo change passed through)
- Rate Transmission on Liabilities (% of repo change passed through)
- Yield on Advances [= prior year + rate effect + mix effect]
- CA Cost (always 0)
- SA Cost [= prior year ± rate change × transmission]
- TD Cost [= prior year ± rate change × transmission]
- Yield on Investments
- Interest Rate on RBI Balances

GROUP 5 — BALANCE SHEET RATIOS:
- Balances with Banks as % of Deposits
- Cash with RBI as % of Deposits
- Investments as % of NDTL
- Fixed Asset Growth Rate
- Other Assets as % of Advances
- Other Liabilities as % of Deposits
- Minority Interest Growth Rate

GROUP 6 — ASSET QUALITY:
- GNPA Ratio by segment (one row per segment)
- Provision Coverage Ratio
- Credit Cost (provisions / avg advances)

GROUP 7 — EFFICIENCY:
- Other Income as % of Interest Earned
- OpEx as % of Advances
- Tax Rate

GROUP 8 — CAPITAL ALLOCATION:
- Dividend Payout Ratio
- Equity Raise (₹ Cr, 0 if none)

Each assumption cell must have a comment explaining the rationale 
and whether it is anchored to management guidance.

### Sheet 5: Advances Mix
Quarterly data table showing advances by segment.
Columns: Q1FY22 through Q4FY[current] (actuals), then annual 
FY[current+1] through FY[current+5] (forecasts)
Rows: Each disclosed segment + Total
Also show: composition % for each segment, YoY growth by segment,
Yield on Advances (quarterly actuals, annual forecasts)

### Sheet 6: Advances Build
Annual forecast of advances by segment.
- Start from latest quarterly actuals
- Apply segment mix assumptions from Assumptions sheet
- Total advances feeds to BS
- Also build GNPA by segment [= segment advances × GNPA ratio assumption]
- Total GNPA provision feeds to PnL provisions line

### Sheet 7: Deposit Schedule
Quarterly actuals then annual forecasts.
- CA, SA, CASA total, Term Deposits, Total Deposits
- CASA ratio, CA/SA split
- Cost of deposits (quarterly actuals, annual forecasts)
- TD cost, SA cost separately
- Total deposit interest cost (feeds to PnL Interest Expended)

### Sheet 8: NDTL
Net Demand and Time Liabilities calculation.
NDTL = Deposits + Borrowings - Interbank assets
- CRR held vs required (4% of NDTL)
- SLR held vs required (18% of NDTL)
- Investments as % of NDTL

### Sheet 9: GNPA Schedule
Quarterly actuals of GNPA by segment.
- Absolute GNPA (₹ Cr) by segment
- Total GNPA, Net NPA, Provisions, PCR
- GNPA ratios by segment (GNPA / segment advances)
Annual forecasts feed from Advances Build sheet.

### Sheet 10: ROE Tree
DuPont decomposition of ROE, annual FY21 through FY[current+5]:
Level 1: ROE = ROA × Equity Multiplier
Level 2: ROA = Net Margin × Asset Turnover
Level 3: 
- NII / Avg Assets (NIM on assets)
- Non-Interest Income / Avg Assets
- OpEx / Avg Assets
- Provisions / Avg Assets  
- Tax / Avg Assets
Level 4:
- Yield on Advances
- Yield on Investments
- Cost of Deposits and Borrowings
- Cost-to-Income Ratio

### Sheet 11: Regulatory Ratios
Annual FY21 through FY[current+5]:
Capital Adequacy:
- Tangible Equity / Total Assets
Reserve Requirements:
- NDTL
- CRR Balance and % of NDTL
- SLR Balance and % of NDTL
Asset Quality:
- GNPA ratio
- Net NPA ratio
- Provision Coverage Ratio
Liquidity:
- CD Ratio
- CASA Ratio
Profitability:
- ROA
- ROE
- NIM
- Cost-to-Income

### Sheet 12: Valuation
Sub-sections:

A) RESIDUAL INCOME VALUATION (RIV)
[This is the primary valuation methodology for banks because 
banks cannot produce free cash flow in the traditional sense — 
capital must stay in the business to support loan growth]
- Cost of Equity (Ke) = Rf + Beta × ERP
- Terminal Growth Rate
- Book value per share by year
- PAT by year
- Equity charge = Ke × beginning book value
- Residual Income = PAT - Equity Charge
- PV of residual income for each forecast year
- Terminal value of residual income
- Equity value = Current BV + PV of RI + PV of terminal RI
- Value per share

B) PEER COMPARISON
Table with: Company, Market Cap, Price, P/E, P/B, Div Yield, ROE
Peer group for Indian private banks:
IndusInd Bank, IDFC First Bank, Bandhan Bank, Karur Vysya Bank, 
City Union Bank, Yes Bank, RBL Bank, South Indian Bank
(Remove and add peers as appropriate for the specific bank)
- Peer mean and median multiples
- Implied value range from P/B and P/E

C) DIVIDEND DISCOUNT MODEL (secondary)
- Forecast dividends per share
- Terminal dividend growth rate
- DDM value per share

### Sheet 13: Football Field
Visual summary of valuation ranges:
- RIV: low / mid / high
- P/B implied: low / mid / high  
- P/E implied: low / mid / high
- DDM: low / mid / high
- 52-week range: low / high
- Analyst consensus: low / high (if available)
- Overall range
- Current market price marked

### Sheet 14: Beta
- Weekly price data for stock and Nifty Bank index (3 years)
- Weekly returns for both series
- OLS regression output (use Excel's LINEST or equivalent)
- Beta, R-squared, standard error
- Beta used in valuation clearly labeled

### Sheet 15: Peer Comps
Detailed peer comparison table with trailing and forward multiples.

### Sheet 16: Thesis
Structured investment note:
1. RECOMMENDATION AND TARGET PRICE
2. INVESTMENT CASE
3. KEY MODEL ASSUMPTIONS
4. WHERE WE COULD BE WRONG
5. RECENT DEVELOPMENTS
6. RISKS
7. VALUATION

## ASSUMPTION RANGES FOR INDIAN PRIVATE BANKS
Use these as sanity checks. Flag to user if generated assumptions 
fall outside these ranges.

- Loan growth: 10-25% YoY (strong banks); 5-15% (weaker banks)
- NIM: 2.8-4.5% depending on mix
- CASA ratio: 25-50%
- C/I ratio: 40-55%
- Credit cost: 0.4-1.5% of advances (normal cycle)
- ROA: 0.8-1.8%
- ROE: 10-18%
- GNPA ratio: 1.5-5% (healthy bank), flag if >5%
- PCR: 65-80%

## VALUATION METHODOLOGY RATIONALE
Banks are valued on RIV (also called Excess Return Model) rather 
than DCF because:
1. Interest expense is an operating item, not a financing item
2. Working capital is not meaningful for banks
3. Free cash flow is not meaningful — capital retained supports 
   future growth
4. Book value is the anchor — the question is how much premium 
   to book is justified by excess returns (ROE above Ke)
P/B is the most common market multiple used alongside RIV.
P/E is secondary. DDM is used as a cross-check for high-dividend banks.

## Key Metrics & Benchmarks
- NIM Target Range: 3.0-4.5% for private banks, 2.5-3.5% for PSU banks
- CASA Ratio Target: 40-50% for strong franchises
- Credit Cost Normal: 0.5-1.0% of advances
- ROE Target: 15-18% for best-in-class
- Cost-to-Income: 40-50% for efficient banks
- GNPA Threshold: <2% is excellent, 2-3% is good, >4% needs monitoring
- PCR Minimum: 70%+ for adequate coverage

## Risk Factors
- Interest rate cycle risk (NIM compression in falling rate environment)
- Asset quality deterioration in stressed segments (MFI, unsecured retail)
- CASA erosion due to competition from fintechs and small finance banks
- Regulatory changes (PSL norms, digital lending guidelines)
- Concentration risk in specific geographies or segments
- Management succession and governance issues
- Technology disruption from digital-only players

## Modeling Notes
- Always use consolidated financials for banks with subsidiaries
- Adjust for one-time items (treasury gains/losses, exceptional provisions)
- Watch for merger accounting adjustments (e.g., HDFC-HDFC Bank)
- CD ratio above 85% indicates potential liquidity stress
- NDTL-based ratios more meaningful than deposit-based for regulatory analysis
- Quarter-end window dressing common for CD and CASA ratios

## Observed Data (Auto-updated by Mosaic)
- ICICIBANK FY26: ICICI Bank FY26 (Feb 2026 analysis): India's 2nd largest private bank with market cap ₹10 lakh crore. Trading at 2.87x P/B (19.1x P/E) vs book value ₹487.64. Key metrics: ROE 17-18%, NIM 4.0-4.2%, CASA ratio 43-45%, GNPA <2.5%, NNPA <0.6%, Credit Cost 0.50-0.65%, C/I ratio 40-42%. Strong retail franchise with digital banking leadership. RIV fair value 3.0x P/B (₹1,463) with target price ₹1,520 (3.1x FY27E book), implying 8.8% upside. BUY rating. Best-in-class private bank with sustainable competitive advantages in retail banking and operational efficiency. (source: Financial Model Feb 23, 2026, added: 2026-02-23)
- SBIN FY26: SBI FY25: India's largest PSU bank trading at 1.9x P/B (13.2x P/E) with book value \u20b9641/share. Achieved ROE 17-18%, NIM 3.0-3.2%, CASA ratio 43-45%, GNPA <2.5%, Credit Cost 0.6-0.75%. Market cap \u20b911.2 lakh crore. RIV fair value 1.35x P/B suggesting overvaluation. Best-in-class PSU bank but premium stretched. (source: Annual Report FY25 and Analysis Feb 22, 2026, added: 2026-02-22)
- HDFCBANK FY26: HDFC Bank FY25 (Feb 2026 analysis): Post-merger with HDFC Ltd (July 2023) created India's 3rd largest bank. Current metrics: NIM 3.45%, CASA 40-42% (recovering from pre-merger 47-48%), ROE 15-16% normalizing to 17-18% by FY27-28, GNPA <1.5%, Credit Cost 0.45-0.55%, C/I ratio 43-45%. CD ratio elevated at 105-110% requiring deposit mobilization. Trading at 2.48x P/B (20.4x P/E) vs fair value 2.86x P/B, target price ₹1,050 (15% upside). Book value ₹367/share. Integration pressures temporary; franchise quality intact. (source: FY25 Annual Report and Financial Model Feb 22, 2026, added: 2026-02-22)
- HDFCBANK FY26: HDFC Bank Feb 2026 analysis: Post-merger (Jul 2023) with HDFC Ltd creating India's 3rd largest bank. Key metrics - NIM 3.4-3.6%, CASA 40-42% (recovering from pre-merger 47-48%), ROE 15-16% in FY25 normalizing to 17-18% by FY27-28, GNPA <1.5%, Credit Cost 0.45-0.55%, C/I ratio 43-45% improving to 42-44%. CD ratio elevated at 105-110% requiring normalization. Trading at 2.5x P/B (20.4x P/E) with RIV fair value 2.86x P/B justifying target price ₹1,050 (15% upside). Book value ₹367/share. (source: FY25 Annual Report and Mosaic Analysis Feb 22, 2026, added: 2026-02-22)
- HDFCBANK FY26: HDFC Bank FY25: Post-merger with HDFC Ltd, emerged as India's 3rd largest bank. Target NIM 3.4-3.6%, CASA ratio 40-42%, Credit cost 0.4-0.6%, ROE 16-17%, C/I ratio 42-45%. P/B trading at 2.5x with 20.4x P/E. (source: Annual Report FY25, added: 2026-02-22)
- HDFCBANK FY26: Best-in-class private bank valuation (Feb 2026): RIV methodology with ROE 17.5%, COE 12%, terminal growth 10% justifies P/B of 2.86x. Premium banks with ROE >17% and GNPA <1.5% trade at 2.5-3.0x P/B range. (source: Valuation Analysis Feb 2026, added: 2026-02-22)
- HDFCBANK FY26: HDFC Bank post-merger (July 2023): NIM ~3.45%, CASA 43%, Credit Cost 0.45-0.55%, ROE 17-18%, GNPA 1.25%, Cost-to-Income 43-44%. Trading at 2.5x P/B, 20.4x P/E. Merger integration creating temporary NIM pressure but long-term franchise strength intact. (source: FY25 Annual Report and model assumptions, added: 2026-02-22)
- HDFCBANK FY26: Premium private bank valuation Feb 2026: HDFC Bank at 2.5x P/B and 20x P/E, ICICI Bank at ~2.8x P/B, Axis Bank at ~1.9x P/B, Kotak Bank at ~2.6x P/B. Best-in-class banks with ROE >17% and GNPA <1.5% command 2.5-3.0x P/B (source: Market data as of Feb 22, 2026, added: 2026-02-22)
- HDFCBANK FY26: Post large merger integration: Temporary pressure on CASA ratio, NIM compression, elevated LDR are normal. Recovery timeline typically 18-24 months. Key metrics to monitor: quarterly CASA improvement, deposit growth vs loan growth, cross-sell traction (source: HDFC-HDFC Bank merger analysis (Jul 2023 merger, observed Feb 2026), added: 2026-02-22)
- HDFCBANK FY26: HDFC Bank FY25 post-merger: CASA ratio 40-42% (down from pre-merger 47-48%), NIM ~3.4-3.6%, ROE impacted by merger to ~15-16% normalizing to 17-18% by FY27-28, GNPA <1.5%, Credit-Deposit ratio elevated at 105-110% requiring normalization, Cost-to-Income ratio 42-45% (source: Annual Report FY25 and market data as of Feb 2026, added: 2026-02-22)
- SBIN FY26: PSU bank valuation: RIV fair P/B of 2.5x achievable with ROE of 15%, Ke of 12%, and terminal growth of 10%. Current SBI trades at 1.9x P/B suggesting upside potential as ROE improves (source: Valuation Analysis Feb 2026, added: 2026-02-22)
- SBIN FY26: SBI FY25: Strong deposit and fee income growth, asset quality improving with GNPA trending below 2.5%, CASA ratio maintained above 40%, trading at P/B of 1.9x with book value of ₹641 (source: Annual Report FY2024-25, added: 2026-02-22)
- HDFCBANK FY26: HDFC Bank post-merger (July 2023): NIM ~3.45%, CASA 43%, Credit Cost 0.45-0.55%, ROE 17-18%, GNPA 1.25%, Cost-to-Income 43-44%. Trading at 2.5x P/B, 20.4x P/E. Merger integration creating temporary NIM pressure but long-term franchise strength intact. (source: FY25 Annual Report and model assumptions, added: 2026-02-22)
- HDFCBANK FY26: HDFC Bank post-merger: NIM 3.45%, CASA 43% improving to 45%, GNPA 1.25%, NNPA 0.35%, ROE 17-18%, Credit Cost 0.45-0.55%, C/I ratio 43-44%. Trading at P/B 2.48x vs historical 2.8-3.2x. Merger with HDFC Ltd completed July 2023. (source: FY25 Annual Report and cached assumptions as of Feb 2026, added: 2026-02-22)

