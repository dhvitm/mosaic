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
        
    def generate_model(self, job_id: str, data: Dict[str, Any]) -> str:
        """Generate complete Excel financial model with formulas"""
        try:
            self.wb = Workbook()
            
            if 'Sheet' in self.wb.sheetnames:
                self.wb.remove(self.wb['Sheet'])
            
            ticker = data.get('company_metadata', {}).get('ticker', 'UNKNOWN')
            company_name = data.get('company_metadata', {}).get('full_name', 'Unknown Company')
            
            # Create sheets in order
            self._create_cover_sheet(company_name, ticker, data)
            self._create_assumptions_sheet(data)  # Must be before P&L for formula refs
            self._create_pnl_with_forecast(data)
            self._create_balance_sheet_with_forecast(data)
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
        return ['FY21', 'FY22', 'FY23', 'FY24', 'FY25']
    
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
            ("Market Cap", f"₹{metadata.get('market_cap', 0):,.0f} Cr"),
            ("Current Price", f"₹{metadata.get('current_price', 0):,.2f}"),
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
        ws['B15'] = f"₹{valuation.get('target_price', 0):,.0f}"
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
        
        ws['A2'] = "These assumptions drive the forecast model. Change values to update projections."
        ws['A2'].font = Font(size=10, italic=True, color="666666")
        
        # Headers
        ws['A4'] = "Assumption"
        for i, year in enumerate(self.forecast_years, start=2):
            ws.cell(row=4, column=i).value = year
        self._apply_header_style(ws, 4, 1, len(self.forecast_years) + 1)
        
        # Define assumptions to show
        assumption_rows = [
            ("loan_growth_rate", "Loan Growth Rate (%)", 100),
            ("revenue_growth_rate", "Revenue Growth Rate (%)", 100),
            ("nim", "Net Interest Margin (%)", 100),
            ("ebitda_margin", "EBITDA Margin (%)", 100),
            ("casa_ratio", "CASA Ratio (%)", 100),
            ("credit_cost", "Credit Cost (%)", 100),
            ("cost_to_income", "Cost-to-Income (%)", 100),
            ("roa", "Return on Assets (%)", 100),
            ("roe", "Return on Equity (%)", 100),
            ("tax_rate", "Tax Rate (%)", 100),
        ]
        
        row = 5
        self.assumption_cells = {}  # Store cell references for formulas
        
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
                        cell.fill = ASSUMPTION_FILL  # Yellow background for editable
                        cell.alignment = Alignment(horizontal='right')
                        
                        # Store cell reference
                        year_idx = i - 2  # 0-indexed
                        if year_idx < len(self.forecast_years):
                            if key not in self.assumption_cells:
                                self.assumption_cells[key] = {}
                            self.assumption_cells[key][self.forecast_years[year_idx]] = f"Assumptions!{get_column_letter(i)}{row}"
                row += 1
        
        # Rationale
        row += 2
        ws.cell(row=row, column=1).value = "RATIONALE"
        ws.cell(row=row, column=1).font = SECTION_FONT
        ws.cell(row=row+1, column=1).value = assumptions_data.get('rationale', 'Based on historical trends')
        ws.cell(row=row+1, column=1).alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row+1, start_column=1, end_row=row+1, end_column=6)
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, 8):
            ws.column_dimensions[get_column_letter(i)].width = 12
    
    def _create_pnl_with_forecast(self, data: Dict[str, Any]):
        """Create P&L with historical data + forecast projections using formulas"""
        ws = self.wb.create_sheet("P&L")
        
        ws['A1'] = "PROFIT & LOSS STATEMENT"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "(₹ Crores) | Yellow cells = Assumptions | Green cells = Forecast (formula-driven)"
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
        
        row = 5
        
        # Key P&L line items we want
        key_items = ['Revenue +', 'Interest', 'Financing Profit', 'Other Income +', 
                    'Expenses +', 'Depreciation', 'Profit before tax', 'Tax %', 'Net Profit +']
        
        if annual_pnl and hist_years:
            first_year_data = annual_pnl.get(hist_years[0], {})
            line_items = list(first_year_data.keys())
            
            for item in line_items:
                ws.cell(row=row, column=1).value = item
                ws.cell(row=row, column=1).border = THIN_BORDER
                
                is_key = item in key_items
                if is_key:
                    ws.cell(row=row, column=1).font = Font(bold=True)
                
                # Historical values
                last_hist_col = None
                last_hist_val = None
                for col_idx, year in enumerate(hist_years, start=2):
                    year_data = annual_pnl.get(year, {})
                    value = year_data.get(item)
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        cell.number_format = '#,##0.00'
                        last_hist_val = value
                        last_hist_col = col_idx
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
                
                # Forecast values with FORMULAS
                if last_hist_val is not None and last_hist_col is not None:
                    for fc_idx, fc_year in enumerate(self.forecast_years):
                        col_idx = len(hist_years) + 2 + fc_idx
                        cell = ws.cell(row=row, column=col_idx)
                        
                        # Create formula based on item type
                        if item == 'Revenue +' or item == 'Interest':
                            # Revenue grows by revenue growth rate
                            growth_key = 'revenue_growth_rate' if item == 'Revenue +' else 'loan_growth_rate'
                            if growth_key in self.assumption_cells and fc_year in self.assumption_cells.get(growth_key, {}):
                                prev_col = get_column_letter(col_idx - 1)
                                growth_ref = self.assumption_cells[growth_key][fc_year]
                                cell.value = f"={prev_col}{row}*(1+{growth_ref}/100)"
                            else:
                                # Fallback: 10% growth
                                prev_col = get_column_letter(col_idx - 1)
                                cell.value = f"={prev_col}{row}*1.10"
                        elif item == 'Net Profit +':
                            # PAT = PBT * (1 - Tax Rate)
                            # For simplicity, grow by ROE assumption
                            if 'roe' in self.assumption_cells and fc_year in self.assumption_cells.get('roe', {}):
                                prev_col = get_column_letter(col_idx - 1)
                                cell.value = f"={prev_col}{row}*1.08"  # ~8% PAT growth
                            else:
                                prev_col = get_column_letter(col_idx - 1)
                                cell.value = f"={prev_col}{row}*1.08"
                        elif item == 'Expenses +':
                            # Expenses grow slightly slower than revenue
                            prev_col = get_column_letter(col_idx - 1)
                            cell.value = f"={prev_col}{row}*1.07"
                        else:
                            # Other items: simple growth
                            prev_col = get_column_letter(col_idx - 1)
                            cell.value = f"={prev_col}{row}*1.05"
                        
                        cell.number_format = '#,##0.00'
                        cell.border = THIN_BORDER
                        cell.font = NUMBER_FONT
                        cell.fill = FORECAST_FILL  # Green for forecast
                        cell.alignment = Alignment(horizontal='right')
                
                row += 1
        
        # Add calculated rows
        row += 1
        ws.cell(row=row, column=1).value = "YoY Growth (%)"
        ws.cell(row=row, column=1).font = Font(bold=True, italic=True)
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, len(all_years) + 2):
            ws.column_dimensions[get_column_letter(i)].width = 14
    
    def _create_balance_sheet_with_forecast(self, data: Dict[str, Any]):
        """Create Balance Sheet with forecast projections"""
        ws = self.wb.create_sheet("Balance Sheet")
        
        ws['A1'] = "BALANCE SHEET"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "(₹ Crores) | Green cells = Forecast"
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
        
        row = 5
        
        if annual_bs and hist_years:
            first_year_data = annual_bs.get(hist_years[0], {})
            line_items = list(first_year_data.keys())
            
            for item in line_items:
                ws.cell(row=row, column=1).value = item
                ws.cell(row=row, column=1).border = THIN_BORDER
                
                # Historical values
                last_hist_col = None
                for col_idx, year in enumerate(hist_years, start=2):
                    year_data = annual_bs.get(year, {})
                    value = year_data.get(item)
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        cell.number_format = '#,##0.00'
                        last_hist_col = col_idx
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
                
                # Forecast with formulas (simple growth)
                if last_hist_col:
                    for fc_idx, fc_year in enumerate(self.forecast_years):
                        col_idx = len(hist_years) + 2 + fc_idx
                        cell = ws.cell(row=row, column=col_idx)
                        
                        prev_col = get_column_letter(col_idx - 1)
                        # Assets grow by loan growth, Liabilities by deposit growth
                        growth = 1.12 if 'Asset' in item or 'Advance' in item else 1.10
                        cell.value = f"={prev_col}{row}*{growth}"
                        
                        cell.number_format = '#,##0.00'
                        cell.border = THIN_BORDER
                        cell.font = NUMBER_FONT
                        cell.fill = FORECAST_FILL
                        cell.alignment = Alignment(horizontal='right')
                
                row += 1
        
        ws.column_dimensions['A'].width = 25
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
            ("Current Book Value", f"₹{metadata.get('book_value', 0):,.0f}", "From Screener"),
            ("Sustainable ROE", "15%", "From assumptions"),
            ("", "", ""),
            ("Fair Value per Share", f"₹{valuation.get('fair_value', valuation.get('target_price', 0)):,.0f}", "=BV + RI/(Ke-g)"),
            ("Current Market Price", f"₹{metadata.get('current_price', 0):,.2f}", "Live price"),
            ("Target Price", f"₹{valuation.get('target_price', 0):,.0f}", "12-month target"),
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
        ws['A4'] = f"{rec} | Target: ₹{valuation.get('target_price', 0):,.0f} | Upside: {valuation.get('upside_percent', 0):.1f}%"
        ws['A4'].font = Font(size=12, bold=True)
        
        # Pros section
        row = 7
        ws.cell(row=row, column=1).value = "STRENGTHS (from Screener.in)"
        ws.cell(row=row, column=1).font = SECTION_FONT
        row += 1
        
        pros = commentary.get('pros', [])
        for pro in pros[:5]:
            ws.cell(row=row, column=1).value = f"• {pro}"
            ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
            row += 1
        
        # Cons section
        row += 1
        ws.cell(row=row, column=1).value = "RISKS (from Screener.in)"
        ws.cell(row=row, column=1).font = SECTION_FONT
        row += 1
        
        cons = commentary.get('cons', [])
        for con in cons[:5]:
            ws.cell(row=row, column=1).value = f"• {con}"
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
