from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, Reference
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Define styles
HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(size=16, bold=True, color="1F4E79")
SECTION_FONT = Font(size=12, bold=True, color="2F5496")
NUMBER_FONT = Font(name="Consolas", size=10)
FORECAST_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
ASSUMPTION_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
ROE_FILL = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

class ExcelGenerator:
    def __init__(self):
        self.wb = None
        self.forecast_years = ['FY26E', 'FY27E', 'FY28E', 'FY29E', 'FY30E']
        # Store row references for formula linking
        self.pnl_rows = {}
        self.bs_rows = {}
        self.assumption_refs = {}
        
    def generate_model(self, job_id: str, data: Dict[str, Any]) -> str:
        """Generate complete Excel financial model with formulas"""
        try:
            self.wb = Workbook()
            
            if 'Sheet' in self.wb.sheetnames:
                self.wb.remove(self.wb['Sheet'])
            
            ticker = data.get('company_metadata', {}).get('ticker', 'UNKNOWN')
            company_name = data.get('company_metadata', {}).get('full_name', 'Unknown Company')
            
            # Create sheets in order - Assumptions first for formula references
            self._create_cover_sheet(company_name, ticker, data)
            self._create_assumptions_sheet(data)  # Must be first for formula refs
            self._create_pnl_with_formulas(data)
            self._create_balance_sheet_with_formulas(data)
            self._create_roe_tree_sheet(data)  # NEW: ROE decomposition
            self._create_quarterly_sheet(data)
            self._create_ratios_sheet(data)
            self._create_valuation_sheet(data)
            self._create_peer_comparison_sheet(data)
            self._create_thesis_sheet(data)
            
            # Save file
            import os
            os.makedirs("/app/generated_models", exist_ok=True)
            filename = f"{ticker}_model_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            filepath = f"/app/generated_models/{filename}"
            self.wb.save(filepath)
            
            logger.info(f"Excel model generated: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating Excel model: {str(e)}")
            raise
    
    def _apply_header_style(self, ws, row: int, start_col: int, end_col: int):
        """Apply header style to a row"""
        for col in range(start_col, end_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = THIN_BORDER
    
    def _get_historical_years(self, data: Dict) -> List[str]:
        """Extract historical years from scraped data"""
        historical = data.get('historical_financials', {})
        annual_pnl = historical.get('annual_pnl', {})
        if annual_pnl:
            years = sorted([y for y in annual_pnl.keys() if y != 'TTM'], key=lambda x: x)
            return years[-5:]  # Last 5 years
        return ['Mar 2021', 'Mar 2022', 'Mar 2023', 'Mar 2024', 'Mar 2025']
    
    def _create_cover_sheet(self, company_name: str, ticker: str, data: Dict[str, Any]):
        """Create cover sheet with summary"""
        ws = self.wb.create_sheet("Cover", 0)
        
        metadata = data.get('company_metadata', {})
        valuation = data.get('valuation', {})
        thesis = data.get('thesis', {})
        
        ws['A1'] = "FINANCIAL MODEL"
        ws['A1'].font = Font(size=24, bold=True, color="1F4E79")
        
        ws['A2'] = company_name
        ws['A2'].font = Font(size=18, bold=True)
        
        ws['A3'] = f"Ticker: {ticker}"
        ws['A3'].font = Font(size=12, color="666666")
        
        ws['A5'] = f"Generated: {datetime.now().strftime('%d %B %Y %H:%M')}"
        ws['A5'].font = Font(size=10, italic=True, color="999999")
        
        # Key Data
        ws['A7'] = "KEY DATA"
        ws['A7'].font = SECTION_FONT
        
        key_data = [
            ("Sector", metadata.get('sector', 'N/A')),
            ("Market Cap", f"Rs.{metadata.get('market_cap', 0):,.0f} Cr"),
            ("Current Price", f"Rs.{metadata.get('current_price', 0):,.2f}"),
        ]
        
        for i, (label, value) in enumerate(key_data, start=8):
            ws[f'A{i}'] = label
            ws[f'B{i}'] = value
            ws[f'B{i}'].font = Font(bold=True)
        
        # Recommendation
        ws['A13'] = "RECOMMENDATION"
        ws['A13'].font = SECTION_FONT
        
        rec = valuation.get('recommendation', 'HOLD')
        rec_color = "00AA00" if rec == "BUY" else "CC0000" if rec == "SELL" else "FF9900"
        
        ws['A14'] = "Rating"
        ws['B14'] = rec
        ws['B14'].font = Font(size=14, bold=True, color=rec_color)
        
        ws['A15'] = "Target Price"
        ws['B15'] = f"Rs.{valuation.get('target_price', 0):,.0f}"
        ws['B15'].font = Font(size=14, bold=True)
        
        ws['A16'] = "Upside"
        ws['B16'] = f"{valuation.get('upside_percent', 0):.1f}%"
        
        # Thesis Summary
        ws['A19'] = "INVESTMENT THESIS"
        ws['A19'].font = SECTION_FONT
        ws['A20'] = thesis.get('summary', f"{rec} recommendation")
        ws['A20'].alignment = Alignment(wrap_text=True)
        
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 30
    
    def _create_assumptions_sheet(self, data: Dict[str, Any]):
        """Create Assumptions sheet - this is the driver sheet for forecasts"""
        ws = self.wb.create_sheet("Assumptions")
        
        assumptions_data = data.get('assumptions', {})
        assumptions = assumptions_data.get('assumptions', {})
        
        ws['A1'] = "FORECAST ASSUMPTIONS"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "Change yellow cells to update projections. All linked sheets will recalculate."
        ws['A2'].font = Font(size=10, italic=True, color="666666")
        
        # Headers
        ws['A4'] = "Assumption"
        for i, year in enumerate(self.forecast_years, start=2):
            ws.cell(row=4, column=i).value = year
        self._apply_header_style(ws, 4, 1, len(self.forecast_years) + 1)
        
        # Define assumptions to show - store cell references for formulas
        assumption_rows = [
            ("revenue_growth_rate", "Revenue Growth Rate (%)", 100),
            ("loan_growth_rate", "Loan/Advances Growth (%)", 100),
            ("nim", "Net Interest Margin (%)", 100),
            ("ebitda_margin", "EBITDA Margin (%)", 100),
            ("operating_expense_growth", "Operating Expense Growth (%)", 100),
            ("depreciation_rate", "Depreciation Rate (%)", 100),
            ("interest_expense_rate", "Interest Expense Rate (%)", 100),
            ("tax_rate", "Effective Tax Rate (%)", 100),
            ("dividend_payout", "Dividend Payout (%)", 100),
            ("roa", "Return on Assets (%)", 100),
            ("roe", "Return on Equity (%)", 100),
            ("casa_ratio", "CASA Ratio (%)", 100),
            ("credit_cost", "Credit Cost (%)", 100),
            ("cost_to_income", "Cost-to-Income (%)", 100),
        ]
        
        row = 5
        self.assumption_refs = {}  # Reset for this generation
        
        for key, label, multiplier in assumption_rows:
            if key in assumptions:
                ws.cell(row=row, column=1).value = label
                ws.cell(row=row, column=1).border = THIN_BORDER
                
                values = assumptions[key]
                if isinstance(values, list):
                    for i, val in enumerate(values[:5], start=2):
                        cell = ws.cell(row=row, column=i)
                        cell.value = round(val * multiplier, 2) if val else 0
                        cell.number_format = '0.00'
                        cell.font = NUMBER_FONT
                        cell.border = THIN_BORDER
                        cell.fill = ASSUMPTION_FILL  # Yellow for editable
                        cell.alignment = Alignment(horizontal='right')
                        
                        # Store cell reference for formulas
                        year_idx = i - 2  # 0-indexed
                        if year_idx < len(self.forecast_years):
                            if key not in self.assumption_refs:
                                self.assumption_refs[key] = {}
                            self.assumption_refs[key][self.forecast_years[year_idx]] = f"Assumptions!${get_column_letter(i)}${row}"
                row += 1
        
        # Add note about defaults if assumptions are sparse
        row += 2
        ws.cell(row=row, column=1).value = "RATIONALE"
        ws.cell(row=row, column=1).font = SECTION_FONT
        ws.cell(row=row+1, column=1).value = assumptions_data.get('rationale', 'Based on historical trends and sector outlook')
        ws.cell(row=row+1, column=1).alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row+1, start_column=1, end_row=row+1, end_column=6)
        
        ws.column_dimensions['A'].width = 30
        for i in range(2, 8):
            ws.column_dimensions[get_column_letter(i)].width = 12
    
    def _create_pnl_with_formulas(self, data: Dict[str, Any]):
        """Create P&L with mechanical linking formulas and projections"""
        ws = self.wb.create_sheet("P&L")
        
        ws['A1'] = "PROFIT & LOSS STATEMENT"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "(Rs. Crores) | Green cells = Forecast with formulas linked to Assumptions"
        ws['A2'].font = Font(size=10, italic=True, color="666666")
        
        # Get historical data
        historical = data.get('historical_financials', {})
        annual_pnl = historical.get('annual_pnl', {})
        
        hist_years = self._get_historical_years(data)
        all_years = hist_years + self.forecast_years
        
        # Headers
        ws['A4'] = "Line Item"
        for i, year in enumerate(all_years, start=2):
            cell = ws.cell(row=4, column=i)
            cell.value = year
            if year in self.forecast_years:
                cell.fill = FORECAST_FILL
        self._apply_header_style(ws, 4, 1, len(all_years) + 1)
        
        # Define P&L structure with formulas
        # We'll create a proper P&L with calculated fields
        pnl_structure = [
            ('Revenue +', 'revenue', True),
            ('Interest', 'interest_income', True),
            ('Other Income +', 'other_income', True),
            ('Total Income', 'total_income', False),  # Calculated
            ('', '', False),  # Spacer
            ('Operating Expenses', 'opex', True),
            ('Employee Cost', 'employee_cost', True),
            ('Interest Expense', 'interest_expense', True),
            ('Depreciation', 'depreciation', True),
            ('Other Expenses', 'other_expenses', True),
            ('Total Expenses', 'total_expenses', False),  # Calculated
            ('', '', False),  # Spacer
            ('Profit before tax', 'pbt', False),  # Calculated
            ('Tax %', 'tax', False),  # Calculated
            ('Net Profit +', 'pat', False),  # Calculated
        ]
        
        row = 5
        hist_col_end = len(hist_years) + 1
        forecast_col_start = len(hist_years) + 2
        
        # Track row numbers for formulas
        self.pnl_rows = {}
        
        # First pass: populate historical data and store row numbers
        for item_name, item_key, is_input in pnl_structure:
            if not item_name:  # Spacer row
                row += 1
                continue
            
            ws.cell(row=row, column=1).value = item_name
            ws.cell(row=row, column=1).border = THIN_BORDER
            
            # Bold key items
            if item_key in ['total_income', 'total_expenses', 'pbt', 'pat']:
                ws.cell(row=row, column=1).font = Font(bold=True)
            
            self.pnl_rows[item_key] = row
            
            # Historical values
            if annual_pnl and hist_years:
                for col_idx, year in enumerate(hist_years, start=2):
                    year_data = annual_pnl.get(year, {})
                    
                    # Map our key to possible screener keys
                    screener_keys = {
                        'revenue': ['Revenue +', 'Sales +', 'Interest Earned', 'Revenue from Operations +'],
                        'interest_income': ['Interest', 'Interest Earned', 'Net Interest Income'],
                        'other_income': ['Other Income +', 'Other Income'],
                        'opex': ['Expenses +', 'Operating Expenses'],
                        'employee_cost': ['Employee Cost', 'Employee Benefit Expense'],
                        'interest_expense': ['Interest', 'Finance Costs', 'Interest Expended'],
                        'depreciation': ['Depreciation', 'Depreciation and Amortisation'],
                        'other_expenses': ['Other Expenses', 'Other expenses'],
                        'pbt': ['Profit before tax', 'PBT'],
                        'tax': ['Tax %', 'Tax'],
                        'pat': ['Net Profit +', 'Net Profit', 'PAT']
                    }
                    
                    value = None
                    for key in screener_keys.get(item_key, [item_name]):
                        if key in year_data:
                            value = year_data[key]
                            break
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        cell.number_format = '#,##0.00'
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
            
            row += 1
        
        # Second pass: Add formulas for forecast years
        # Reset row counter
        row = 5
        for item_name, item_key, is_input in pnl_structure:
            if not item_name:
                row += 1
                continue
            
            # Add formulas for forecast columns
            for fc_idx, fc_year in enumerate(self.forecast_years):
                col_idx = forecast_col_start + fc_idx
                cell = ws.cell(row=row, column=col_idx)
                prev_col = get_column_letter(col_idx - 1)
                curr_col = get_column_letter(col_idx)
                
                if item_key == 'revenue':
                    # Revenue = Previous * (1 + growth rate)
                    growth_ref = self.assumption_refs.get('revenue_growth_rate', {}).get(fc_year)
                    if growth_ref:
                        cell.value = f"={prev_col}{row}*(1+{growth_ref}/100)"
                    else:
                        cell.value = f"={prev_col}{row}*1.10"
                        
                elif item_key == 'interest_income':
                    # Interest income grows with loan growth
                    growth_ref = self.assumption_refs.get('loan_growth_rate', {}).get(fc_year)
                    if growth_ref:
                        cell.value = f"={prev_col}{row}*(1+{growth_ref}/100)"
                    else:
                        cell.value = f"={prev_col}{row}*1.12"
                        
                elif item_key == 'other_income':
                    # Other income: modest growth
                    cell.value = f"={prev_col}{row}*1.05"
                    
                elif item_key == 'total_income':
                    # Total Income = Revenue + Interest + Other
                    rev_row = self.pnl_rows.get('revenue', row-3)
                    int_row = self.pnl_rows.get('interest_income', row-2)
                    oth_row = self.pnl_rows.get('other_income', row-1)
                    cell.value = f"={curr_col}{rev_row}+{curr_col}{int_row}+{curr_col}{oth_row}"
                    cell.font = Font(bold=True)
                    
                elif item_key == 'opex':
                    # Operating expenses grow with revenue but slower
                    growth_ref = self.assumption_refs.get('operating_expense_growth', {}).get(fc_year)
                    if growth_ref:
                        cell.value = f"={prev_col}{row}*(1+{growth_ref}/100)"
                    else:
                        cell.value = f"={prev_col}{row}*1.08"
                        
                elif item_key == 'employee_cost':
                    cell.value = f"={prev_col}{row}*1.08"
                    
                elif item_key == 'interest_expense':
                    # Interest expense linked to rate assumption
                    rate_ref = self.assumption_refs.get('interest_expense_rate', {}).get(fc_year)
                    if rate_ref:
                        cell.value = f"={prev_col}{row}*(1+{rate_ref}/100)"
                    else:
                        cell.value = f"={prev_col}{row}*1.06"
                        
                elif item_key == 'depreciation':
                    # Depreciation grows modestly
                    cell.value = f"={prev_col}{row}*1.05"
                    
                elif item_key == 'other_expenses':
                    cell.value = f"={prev_col}{row}*1.07"
                    
                elif item_key == 'total_expenses':
                    # Total = Sum of all expense line items
                    opex_row = self.pnl_rows.get('opex', row-5)
                    emp_row = self.pnl_rows.get('employee_cost', row-4)
                    int_exp_row = self.pnl_rows.get('interest_expense', row-3)
                    dep_row = self.pnl_rows.get('depreciation', row-2)
                    oth_exp_row = self.pnl_rows.get('other_expenses', row-1)
                    cell.value = f"={curr_col}{opex_row}+{curr_col}{emp_row}+{curr_col}{int_exp_row}+{curr_col}{dep_row}+{curr_col}{oth_exp_row}"
                    cell.font = Font(bold=True)
                    
                elif item_key == 'pbt':
                    # PBT = Total Income - Total Expenses (MECHANICAL LINK)
                    inc_row = self.pnl_rows.get('total_income')
                    exp_row = self.pnl_rows.get('total_expenses')
                    if inc_row and exp_row:
                        cell.value = f"={curr_col}{inc_row}-{curr_col}{exp_row}"
                    else:
                        cell.value = f"={prev_col}{row}*1.08"
                    cell.font = Font(bold=True)
                    
                elif item_key == 'tax':
                    # Tax = PBT * Tax Rate
                    pbt_row = self.pnl_rows.get('pbt')
                    tax_ref = self.assumption_refs.get('tax_rate', {}).get(fc_year)
                    if pbt_row and tax_ref:
                        cell.value = f"={curr_col}{pbt_row}*{tax_ref}/100"
                    else:
                        pbt_row = pbt_row or (row - 1)
                        cell.value = f"={curr_col}{pbt_row}*0.25"
                        
                elif item_key == 'pat':
                    # PAT = PBT - Tax (MECHANICAL LINK)
                    pbt_row = self.pnl_rows.get('pbt')
                    tax_row = self.pnl_rows.get('tax')
                    if pbt_row and tax_row:
                        cell.value = f"={curr_col}{pbt_row}-{curr_col}{tax_row}"
                    else:
                        cell.value = f"={prev_col}{row}*1.08"
                    cell.font = Font(bold=True)
                
                cell.number_format = '#,##0.00'
                cell.border = THIN_BORDER
                cell.fill = FORECAST_FILL
                cell.alignment = Alignment(horizontal='right')
            
            row += 1
        
        # Add YoY Growth row
        row += 1
        ws.cell(row=row, column=1).value = "PAT YoY Growth (%)"
        ws.cell(row=row, column=1).font = Font(bold=True, italic=True)
        pat_row = self.pnl_rows.get('pat')
        if pat_row:
            for col_idx in range(3, len(all_years) + 2):
                cell = ws.cell(row=row, column=col_idx)
                prev_col = get_column_letter(col_idx - 1)
                curr_col = get_column_letter(col_idx)
                cell.value = f"=({curr_col}{pat_row}/{prev_col}{pat_row}-1)*100"
                cell.number_format = '0.0'
                cell.border = THIN_BORDER
                if col_idx >= forecast_col_start:
                    cell.fill = FORECAST_FILL
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, len(all_years) + 2):
            ws.column_dimensions[get_column_letter(i)].width = 14
    
    def _create_balance_sheet_with_formulas(self, data: Dict[str, Any]):
        """Create Balance Sheet with forecast projections linked to assumptions"""
        ws = self.wb.create_sheet("Balance Sheet")
        
        ws['A1'] = "BALANCE SHEET"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "(Rs. Crores) | Green cells = Forecast"
        ws['A2'].font = Font(size=10, italic=True, color="666666")
        
        historical = data.get('historical_financials', {})
        annual_bs = historical.get('annual_bs', {})
        
        hist_years = self._get_historical_years(data)
        all_years = hist_years + self.forecast_years
        
        # Headers
        ws['A4'] = "Line Item"
        for i, year in enumerate(all_years, start=2):
            cell = ws.cell(row=4, column=i)
            cell.value = year
            if year in self.forecast_years:
                cell.fill = FORECAST_FILL
        self._apply_header_style(ws, 4, 1, len(all_years) + 1)
        
        # Balance Sheet structure
        bs_structure = [
            ('ASSETS', '', False),
            ('Share Capital', 'share_capital', True),
            ('Reserves', 'reserves', True),
            ('Total Equity', 'total_equity', False),
            ('', '', False),
            ('Borrowings', 'borrowings', True),
            ('Other Liabilities', 'other_liabilities', True),
            ('Total Liabilities', 'total_liabilities', False),
            ('', '', False),
            ('Fixed Assets', 'fixed_assets', True),
            ('Investments', 'investments', True),
            ('Advances/Loans', 'advances', True),
            ('Other Assets', 'other_assets', True),
            ('Total Assets', 'total_assets', False),
        ]
        
        row = 5
        self.bs_rows = {}
        hist_col_end = len(hist_years) + 1
        forecast_col_start = len(hist_years) + 2
        
        for item_name, item_key, is_input in bs_structure:
            if not item_name:
                row += 1
                continue
            
            ws.cell(row=row, column=1).value = item_name
            ws.cell(row=row, column=1).border = THIN_BORDER
            
            if item_key in ['total_equity', 'total_liabilities', 'total_assets'] or item_name == 'ASSETS':
                ws.cell(row=row, column=1).font = Font(bold=True)
            
            if item_key:
                self.bs_rows[item_key] = row
            
            # Historical values
            if annual_bs and hist_years:
                for col_idx, year in enumerate(hist_years, start=2):
                    year_data = annual_bs.get(year, {})
                    
                    # Map keys
                    bs_keys = {
                        'share_capital': ['Share Capital', 'Equity Share Capital'],
                        'reserves': ['Reserves', 'Reserves and Surplus', 'Other Equity'],
                        'borrowings': ['Borrowings', 'Total Debt', 'Long Term Borrowings'],
                        'other_liabilities': ['Other Liabilities', 'Other liabilities'],
                        'fixed_assets': ['Fixed Assets', 'Property, Plant and Equipment', 'Net Block'],
                        'investments': ['Investments', 'Non-current Investments'],
                        'advances': ['Advances +', 'Loans and Advances', 'Trade Receivables'],
                        'other_assets': ['Other Assets', 'Other assets'],
                        'total_assets': ['Total Assets', 'Total'],
                    }
                    
                    value = None
                    for key in bs_keys.get(item_key, [item_name]):
                        if key in year_data:
                            value = year_data[key]
                            break
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        cell.number_format = '#,##0.00'
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
            
            # Forecast formulas
            for fc_idx, fc_year in enumerate(self.forecast_years):
                col_idx = forecast_col_start + fc_idx
                cell = ws.cell(row=row, column=col_idx)
                prev_col = get_column_letter(col_idx - 1)
                curr_col = get_column_letter(col_idx)
                
                if item_key == 'share_capital':
                    # Share capital stays constant
                    cell.value = f"={prev_col}{row}"
                    
                elif item_key == 'reserves':
                    # Reserves = Previous + Retained Earnings (PAT - Dividends)
                    pat_row = self.pnl_rows.get('pat')
                    div_ref = self.assumption_refs.get('dividend_payout', {}).get(fc_year)
                    if pat_row and div_ref:
                        cell.value = f"={prev_col}{row}+'P&L'!{curr_col}{pat_row}*(1-{div_ref}/100)"
                    elif pat_row:
                        cell.value = f"={prev_col}{row}+'P&L'!{curr_col}{pat_row}*0.7"
                    else:
                        cell.value = f"={prev_col}{row}*1.08"
                        
                elif item_key == 'total_equity':
                    # Total Equity = Share Capital + Reserves
                    sc_row = self.bs_rows.get('share_capital')
                    res_row = self.bs_rows.get('reserves')
                    if sc_row and res_row:
                        cell.value = f"={curr_col}{sc_row}+{curr_col}{res_row}"
                    else:
                        cell.value = f"={prev_col}{row}*1.08"
                    cell.font = Font(bold=True)
                    
                elif item_key == 'borrowings':
                    # Borrowings grow moderately
                    cell.value = f"={prev_col}{row}*1.08"
                    
                elif item_key == 'other_liabilities':
                    cell.value = f"={prev_col}{row}*1.06"
                    
                elif item_key == 'total_liabilities':
                    # Total = Borrowings + Other
                    borr_row = self.bs_rows.get('borrowings')
                    oth_row = self.bs_rows.get('other_liabilities')
                    if borr_row and oth_row:
                        cell.value = f"={curr_col}{borr_row}+{curr_col}{oth_row}"
                    else:
                        cell.value = f"={prev_col}{row}*1.07"
                    cell.font = Font(bold=True)
                    
                elif item_key == 'fixed_assets':
                    cell.value = f"={prev_col}{row}*1.05"
                    
                elif item_key == 'investments':
                    cell.value = f"={prev_col}{row}*1.10"
                    
                elif item_key == 'advances':
                    # Advances grow with loan growth
                    growth_ref = self.assumption_refs.get('loan_growth_rate', {}).get(fc_year)
                    if growth_ref:
                        cell.value = f"={prev_col}{row}*(1+{growth_ref}/100)"
                    else:
                        cell.value = f"={prev_col}{row}*1.12"
                        
                elif item_key == 'other_assets':
                    cell.value = f"={prev_col}{row}*1.05"
                    
                elif item_key == 'total_assets':
                    # Total Assets = Equity + Liabilities (should equal asset sum)
                    eq_row = self.bs_rows.get('total_equity')
                    liab_row = self.bs_rows.get('total_liabilities')
                    if eq_row and liab_row:
                        cell.value = f"={curr_col}{eq_row}+{curr_col}{liab_row}"
                    else:
                        cell.value = f"={prev_col}{row}*1.08"
                    cell.font = Font(bold=True)
                
                cell.number_format = '#,##0.00'
                cell.border = THIN_BORDER
                cell.fill = FORECAST_FILL
                cell.alignment = Alignment(horizontal='right')
            
            row += 1
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, len(all_years) + 2):
            ws.column_dimensions[get_column_letter(i)].width = 14
    
    def _create_roe_tree_sheet(self, data: Dict[str, Any]):
        """Create ROE Decomposition Tree (DuPont Analysis)"""
        ws = self.wb.create_sheet("ROE Tree")
        
        ws['A1'] = "ROE DECOMPOSITION (DUPONT ANALYSIS)"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "ROE = Net Profit Margin x Asset Turnover x Equity Multiplier"
        ws['A2'].font = Font(size=10, italic=True, color="666666")
        
        hist_years = self._get_historical_years(data)
        all_years = hist_years + self.forecast_years
        
        # Headers
        ws['A4'] = "Metric"
        for i, year in enumerate(all_years, start=2):
            cell = ws.cell(row=4, column=i)
            cell.value = year
            if year in self.forecast_years:
                cell.fill = FORECAST_FILL
        self._apply_header_style(ws, 4, 1, len(all_years) + 1)
        
        forecast_col_start = len(hist_years) + 2
        
        # ROE Tree structure
        roe_items = [
            ("", "", "section"),
            ("PROFITABILITY", "", "section"),
            ("Net Profit (PAT)", "pat", "link"),
            ("Revenue", "revenue", "link"),
            ("Net Profit Margin (%)", "npm", "calc"),
            ("", "", "spacer"),
            ("EFFICIENCY", "", "section"),
            ("Revenue", "revenue2", "link"),
            ("Average Total Assets", "avg_assets", "link"),
            ("Asset Turnover (x)", "asset_turnover", "calc"),
            ("", "", "spacer"),
            ("LEVERAGE", "", "section"),
            ("Average Total Assets", "avg_assets2", "link"),
            ("Average Equity", "avg_equity", "link"),
            ("Equity Multiplier (x)", "eq_multiplier", "calc"),
            ("", "", "spacer"),
            ("ROE CALCULATION", "", "section"),
            ("ROE (%)", "roe", "final"),
            ("ROE Check: NPM x AT x EM (%)", "roe_check", "verify"),
        ]
        
        row = 5
        roe_rows = {}
        
        for label, key, item_type in roe_items:
            if item_type == "spacer":
                row += 1
                continue
            
            ws.cell(row=row, column=1).value = label
            ws.cell(row=row, column=1).border = THIN_BORDER
            
            if item_type == "section":
                ws.cell(row=row, column=1).font = Font(bold=True, color="1F4E79")
                ws.cell(row=row, column=1).fill = ROE_FILL
                for col in range(2, len(all_years) + 2):
                    ws.cell(row=row, column=col).fill = ROE_FILL
                    ws.cell(row=row, column=col).border = THIN_BORDER
            else:
                if key:
                    roe_rows[key] = row
                
                for fc_idx, year in enumerate(all_years):
                    col_idx = fc_idx + 2
                    cell = ws.cell(row=row, column=col_idx)
                    curr_col = get_column_letter(col_idx)
                    
                    is_forecast = year in self.forecast_years
                    
                    # Link to P&L and Balance Sheet
                    if key == 'pat':
                        pat_row = self.pnl_rows.get('pat')
                        if pat_row:
                            cell.value = f"='P&L'!{curr_col}{pat_row}"
                            
                    elif key in ['revenue', 'revenue2']:
                        rev_row = self.pnl_rows.get('revenue')
                        if rev_row:
                            cell.value = f"='P&L'!{curr_col}{rev_row}"
                            
                    elif key == 'npm':
                        # Net Profit Margin = PAT / Revenue * 100
                        pat_r = roe_rows.get('pat')
                        rev_r = roe_rows.get('revenue')
                        if pat_r and rev_r:
                            cell.value = f"=IF({curr_col}{rev_r}=0,0,{curr_col}{pat_r}/{curr_col}{rev_r}*100)"
                        cell.number_format = '0.00'
                        cell.font = Font(bold=True)
                        
                    elif key in ['avg_assets', 'avg_assets2']:
                        assets_row = self.bs_rows.get('total_assets')
                        if assets_row and col_idx > 2:
                            prev_col = get_column_letter(col_idx - 1)
                            cell.value = f"=('Balance Sheet'!{curr_col}{assets_row}+'Balance Sheet'!{prev_col}{assets_row})/2"
                        elif assets_row:
                            cell.value = f"='Balance Sheet'!{curr_col}{assets_row}"
                            
                    elif key == 'avg_equity':
                        eq_row = self.bs_rows.get('total_equity')
                        if eq_row and col_idx > 2:
                            prev_col = get_column_letter(col_idx - 1)
                            cell.value = f"=('Balance Sheet'!{curr_col}{eq_row}+'Balance Sheet'!{prev_col}{eq_row})/2"
                        elif eq_row:
                            cell.value = f"='Balance Sheet'!{curr_col}{eq_row}"
                            
                    elif key == 'asset_turnover':
                        # Asset Turnover = Revenue / Avg Assets
                        rev_r = roe_rows.get('revenue2')
                        assets_r = roe_rows.get('avg_assets')
                        if rev_r and assets_r:
                            cell.value = f"=IF({curr_col}{assets_r}=0,0,{curr_col}{rev_r}/{curr_col}{assets_r})"
                        cell.number_format = '0.00'
                        cell.font = Font(bold=True)
                        
                    elif key == 'eq_multiplier':
                        # Equity Multiplier = Avg Assets / Avg Equity
                        assets_r = roe_rows.get('avg_assets2')
                        eq_r = roe_rows.get('avg_equity')
                        if assets_r and eq_r:
                            cell.value = f"=IF({curr_col}{eq_r}=0,0,{curr_col}{assets_r}/{curr_col}{eq_r})"
                        cell.number_format = '0.00'
                        cell.font = Font(bold=True)
                        
                    elif key == 'roe':
                        # ROE = PAT / Avg Equity * 100
                        pat_r = roe_rows.get('pat')
                        eq_r = roe_rows.get('avg_equity')
                        if pat_r and eq_r:
                            cell.value = f"=IF({curr_col}{eq_r}=0,0,{curr_col}{pat_r}/{curr_col}{eq_r}*100)"
                        cell.number_format = '0.00'
                        cell.font = Font(bold=True, size=12, color="1F4E79")
                        
                    elif key == 'roe_check':
                        # ROE Check = NPM * AT * EM (should equal ROE)
                        npm_r = roe_rows.get('npm')
                        at_r = roe_rows.get('asset_turnover')
                        em_r = roe_rows.get('eq_multiplier')
                        if npm_r and at_r and em_r:
                            cell.value = f"={curr_col}{npm_r}/100*{curr_col}{at_r}*{curr_col}{em_r}*100"
                        cell.number_format = '0.00'
                        cell.font = Font(italic=True, color="666666")
                    
                    if is_forecast and item_type != "section":
                        cell.fill = FORECAST_FILL
                    
                    cell.border = THIN_BORDER
                    cell.alignment = Alignment(horizontal='right')
                    if not cell.number_format:
                        cell.number_format = '#,##0.00'
            
            row += 1
        
        # Add explanation
        row += 2
        ws.cell(row=row, column=1).value = "INTERPRETATION"
        ws.cell(row=row, column=1).font = SECTION_FONT
        row += 1
        ws.cell(row=row, column=1).value = "ROE = Net Profit Margin x Asset Turnover x Equity Multiplier"
        row += 1
        ws.cell(row=row, column=1).value = "- Net Profit Margin: How much profit per rupee of revenue (profitability)"
        row += 1
        ws.cell(row=row, column=1).value = "- Asset Turnover: How efficiently assets generate revenue (efficiency)"
        row += 1
        ws.cell(row=row, column=1).value = "- Equity Multiplier: Financial leverage (higher = more debt)"
        
        ws.column_dimensions['A'].width = 35
        for i in range(2, len(all_years) + 2):
            ws.column_dimensions[get_column_letter(i)].width = 14
    
    def _create_quarterly_sheet(self, data: Dict[str, Any]):
        """Create Quarterly Results sheet"""
        ws = self.wb.create_sheet("Quarterly")
        
        ws['A1'] = "QUARTERLY RESULTS"
        ws['A1'].font = TITLE_FONT
        
        operational = data.get('operational_data', {})
        quarterly = operational.get('quarterly_results', {})
        
        if quarterly:
            quarters = sorted(quarterly.keys(), key=lambda x: x)[-12:]
        else:
            quarters = []
        
        ws['A3'] = "Line Item"
        for i, q in enumerate(quarters, start=2):
            ws.cell(row=3, column=i).value = q
        if quarters:
            self._apply_header_style(ws, 3, 1, len(quarters) + 1)
        
        row = 4
        if quarterly and quarters:
            first_q_data = quarterly.get(quarters[0], {})
            for item in list(first_q_data.keys()):
                ws.cell(row=row, column=1).value = item
                ws.cell(row=row, column=1).border = THIN_BORDER
                
                for col_idx, q in enumerate(quarters, start=2):
                    q_data = quarterly.get(q, {})
                    value = q_data.get(item)
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        cell.number_format = '#,##0.00'
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
                
                row += 1
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, max(len(quarters) + 2, 3)):
            ws.column_dimensions[get_column_letter(i)].width = 12
    
    def _create_ratios_sheet(self, data: Dict[str, Any]):
        """Create Key Ratios sheet"""
        ws = self.wb.create_sheet("Key Ratios")
        
        ws['A1'] = "KEY FINANCIAL RATIOS"
        ws['A1'].font = TITLE_FONT
        
        historical = data.get('historical_financials', {})
        ratios = historical.get('ratios', {})
        
        if ratios:
            years = sorted([y for y in ratios.keys() if y != 'TTM'], key=lambda x: x)[-10:]
        else:
            years = []
        
        ws['A3'] = "Ratio"
        for i, year in enumerate(years, start=2):
            ws.cell(row=3, column=i).value = year
        if years:
            self._apply_header_style(ws, 3, 1, len(years) + 1)
        
        row = 4
        if ratios and years:
            first_year_data = ratios.get(years[0], {})
            for item in list(first_year_data.keys()):
                ws.cell(row=row, column=1).value = item
                ws.cell(row=row, column=1).border = THIN_BORDER
                
                for col_idx, year in enumerate(years, start=2):
                    year_data = ratios.get(year, {})
                    value = year_data.get(item)
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        cell.number_format = '0.00'
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
                
                row += 1
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, max(len(years) + 2, 3)):
            ws.column_dimensions[get_column_letter(i)].width = 12
    
    def _create_valuation_sheet(self, data: Dict[str, Any]):
        """Create Valuation sheet with RIV model"""
        ws = self.wb.create_sheet("Valuation")
        
        valuation = data.get('valuation', {})
        metadata = data.get('company_metadata', {})
        
        ws['A1'] = "VALUATION"
        ws['A1'].font = TITLE_FONT
        
        # RIV Section
        ws['A3'] = "RESIDUAL INCOME VALUATION (RIV)"
        ws['A3'].font = SECTION_FONT
        
        ws['A5'] = "Parameter"
        ws['B5'] = "Value"
        ws['C5'] = "Formula/Note"
        self._apply_header_style(ws, 5, 1, 3)
        
        riv_params = [
            ("Risk-Free Rate (Rf)", "7.0%", "10-year G-Sec yield"),
            ("Equity Risk Premium", "6.0%", "India market premium"),
            ("Beta", "1.0", "Large-cap bank assumption"),
            ("Cost of Equity (Ke)", f"{valuation.get('cost_of_equity', 13.0):.1f}%", "=Rf + Beta*ERP"),
            ("Terminal Growth (g)", f"{valuation.get('terminal_growth', 4.0):.1f}%", "Long-term GDP growth"),
            ("", "", ""),
            ("Current Book Value", f"Rs.{metadata.get('book_value', 0):,.0f}", "From Screener"),
            ("Sustainable ROE", "15%", "From assumptions"),
            ("", "", ""),
            ("Fair Value per Share", f"Rs.{valuation.get('fair_value', valuation.get('target_price', 0)):,.0f}", "=BV + RI/(Ke-g)"),
            ("Current Market Price", f"Rs.{metadata.get('current_price', 0):,.2f}", "Live price"),
            ("Target Price", f"Rs.{valuation.get('target_price', 0):,.0f}", "12-month target"),
            ("Upside/Downside", f"{valuation.get('upside_percent', 0):.1f}%", "=(TP-CMP)/CMP"),
        ]
        
        row = 6
        for label, value, note in riv_params:
            ws.cell(row=row, column=1).value = label
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=2).value = value
            ws.cell(row=row, column=2).border = THIN_BORDER
            ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
            ws.cell(row=row, column=3).value = note
            ws.cell(row=row, column=3).font = Font(size=9, italic=True, color="666666")
            
            if label in ["Fair Value per Share", "Target Price", "Upside/Downside"]:
                ws.cell(row=row, column=1).font = Font(bold=True)
                ws.cell(row=row, column=2).font = Font(bold=True)
            row += 1
        
        # Recommendation
        row += 2
        ws.cell(row=row, column=1).value = "RECOMMENDATION"
        ws.cell(row=row, column=1).font = SECTION_FONT
        row += 1
        rec = valuation.get('recommendation', 'HOLD')
        ws.cell(row=row, column=1).value = rec
        rec_color = "00AA00" if rec == "BUY" else "CC0000" if rec == "SELL" else "FF9900"
        ws.cell(row=row, column=1).font = Font(size=20, bold=True, color=rec_color)
        
        row += 2
        ws.cell(row=row, column=1).value = valuation.get('rationale', '')
        ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 30
    
    def _create_peer_comparison_sheet(self, data: Dict[str, Any]):
        """Create Peer Comparison sheet"""
        ws = self.wb.create_sheet("Peer Comparison")
        
        ws['A1'] = "PEER COMPARISON"
        ws['A1'].font = TITLE_FONT
        
        commentary = data.get('management_commentary', {})
        peers = commentary.get('peer_comparison', [])
        
        if not peers:
            ws['A3'] = "No peer data available"
            return
        
        # Get columns from first peer
        if peers:
            columns = ['name'] + [k for k in peers[0].keys() if k != 'name']
            
            # Headers
            for i, col in enumerate(columns, start=1):
                ws.cell(row=3, column=i).value = col.replace('_', ' ').title()
            self._apply_header_style(ws, 3, 1, len(columns))
            
            # Data
            for row_idx, peer in enumerate(peers, start=4):
                for col_idx, col in enumerate(columns, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    value = peer.get(col)
                    if value is not None:
                        cell.value = value
                        if isinstance(value, (int, float)):
                            cell.number_format = '#,##0.00'
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
        
        for i in range(1, len(columns) + 1):
            ws.column_dimensions[get_column_letter(i)].width = 15
    
    def _create_thesis_sheet(self, data: Dict[str, Any]):
        """Create Investment Thesis sheet"""
        ws = self.wb.create_sheet("Thesis")
        
        thesis = data.get('thesis', {})
        valuation = data.get('valuation', {})
        metadata = data.get('company_metadata', {})
        commentary = data.get('management_commentary', {})
        
        ws['A1'] = "INVESTMENT THESIS"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = f"{metadata.get('full_name', 'Company')} ({metadata.get('ticker', '')})"
        ws['A2'].font = Font(size=14, bold=True)
        
        # Summary box
        rec = valuation.get('recommendation', 'HOLD')
        ws['A4'] = f"{rec} | Target: Rs.{valuation.get('target_price', 0):,.0f} | Upside: {valuation.get('upside_percent', 0):.1f}%"
        ws['A4'].font = Font(size=12, bold=True)
        
        # Pros section
        row = 7
        ws.cell(row=row, column=1).value = "STRENGTHS (from Screener.in)"
        ws.cell(row=row, column=1).font = SECTION_FONT
        row += 1
        
        pros = commentary.get('pros', [])
        for pro in pros[:5]:
            ws.cell(row=row, column=1).value = f"* {pro}"
            ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
            row += 1
        
        # Cons section
        row += 1
        ws.cell(row=row, column=1).value = "RISKS (from Screener.in)"
        ws.cell(row=row, column=1).font = SECTION_FONT
        row += 1
        
        cons = commentary.get('cons', [])
        for con in cons[:5]:
            ws.cell(row=row, column=1).value = f"* {con}"
            ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
            row += 1
        
        # Full thesis
        row += 2
        ws.cell(row=row, column=1).value = "DETAILED ANALYSIS"
        ws.cell(row=row, column=1).font = SECTION_FONT
        row += 1
        
        thesis_text = thesis.get('full_text', 'See valuation and assumptions sheets for details.')
        ws.cell(row=row, column=1).value = thesis_text
        ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True, vertical='top')
        
        ws.column_dimensions['A'].width = 100
        ws.row_dimensions[row].height = 300
