from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Define styles
HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(size=16, bold=True, color="1F4E79")
SECTION_FONT = Font(size=12, bold=True, color="2F5496")
NUMBER_FONT = Font(name="Consolas", size=10)
THIN_BORDER = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

class ExcelGenerator:
    def __init__(self):
        self.wb = None
        self.years = ['FY21', 'FY22', 'FY23', 'FY24', 'FY25', 'FY26E', 'FY27E', 'FY28E', 'FY29E', 'FY30E']
        self.forecast_years = ['FY26E', 'FY27E', 'FY28E', 'FY29E', 'FY30E']
    
    def generate_model(self, job_id: str, data: Dict[str, Any]) -> str:
        """
        Generate complete Excel financial model
        Returns path to the generated file
        """
        try:
            self.wb = Workbook()
            
            # Remove default sheet
            if 'Sheet' in self.wb.sheetnames:
                self.wb.remove(self.wb['Sheet'])
            
            ticker = data.get('company_metadata', {}).get('ticker', 'UNKNOWN')
            company_name = data.get('company_metadata', {}).get('full_name', 'Unknown Company')
            
            # Create all sheets with real data
            self._create_cover_sheet(company_name, ticker, data)
            self._create_assumptions_sheet(data)
            self._create_pnl_sheet(data)
            self._create_balance_sheet(data)
            self._create_valuation_sheet(data)
            self._create_thesis_sheet(data)
            self._create_key_metrics_sheet(data)
            
            # Ensure output directory exists
            import os
            os.makedirs("/app/generated_models", exist_ok=True)
            
            # Save file
            filename = f"{ticker}_model_{datetime.now().strftime('%Y%m%d')}.xlsx"
            filepath = f"/app/generated_models/{filename}"
            self.wb.save(filepath)
            
            logger.info(f"Excel model generated: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating Excel model: {str(e)}")
            raise
    
    def _apply_header_style(self, ws, row: int, cols: int):
        """Apply header style to a row"""
        for col in range(1, cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = THIN_BORDER
    
    def _create_cover_sheet(self, company_name: str, ticker: str, data: Dict[str, Any]):
        """Create cover sheet with summary"""
        ws = self.wb.create_sheet("Cover", 0)
        
        metadata = data.get('company_metadata', {})
        valuation = data.get('valuation', {})
        thesis = data.get('thesis', {})
        
        # Title
        ws['A1'] = "FINANCIAL MODEL"
        ws['A1'].font = Font(size=24, bold=True, color="1F4E79")
        
        ws['A2'] = company_name
        ws['A2'].font = Font(size=18, bold=True)
        
        ws['A3'] = f"Ticker: {ticker} | NSE: {metadata.get('nse_code', ticker)}"
        ws['A3'].font = Font(size=12, color="666666")
        
        ws['A5'] = f"Generated: {datetime.now().strftime('%d %B %Y')}"
        ws['A5'].font = Font(size=10, italic=True, color="999999")
        
        # Key Data Section
        ws['A7'] = "KEY DATA"
        ws['A7'].font = SECTION_FONT
        
        key_data = [
            ("Sector", metadata.get('sector', 'N/A')),
            ("Industry", metadata.get('industry', 'N/A')),
            ("Market Cap", f"₹{metadata.get('market_cap', 0):,.0f} Cr"),
            ("Current Price", f"₹{metadata.get('current_price', 0):,.2f}"),
            ("Face Value", f"₹{metadata.get('face_value', 10)}")
        ]
        
        for i, (label, value) in enumerate(key_data, start=8):
            ws[f'A{i}'] = label
            ws[f'A{i}'].font = Font(color="666666")
            ws[f'B{i}'] = value
            ws[f'B{i}'].font = Font(bold=True)
        
        # Recommendation Section
        ws['A15'] = "RECOMMENDATION"
        ws['A15'].font = SECTION_FONT
        
        rec = valuation.get('recommendation', 'HOLD')
        rec_color = "00AA00" if rec == "BUY" else "CC0000" if rec == "SELL" else "FF9900"
        
        ws['A16'] = "Rating"
        ws['B16'] = rec
        ws['B16'].font = Font(size=14, bold=True, color=rec_color)
        
        ws['A17'] = "Target Price"
        ws['B17'] = f"₹{valuation.get('target_price', 0):,.0f}"
        ws['B17'].font = Font(size=14, bold=True)
        
        ws['A18'] = "Upside/Downside"
        upside = valuation.get('upside_percent', valuation.get('upside', 0))
        ws['B18'] = f"{upside}%" if isinstance(upside, (int, float)) else str(upside)
        
        ws['A19'] = "Cost of Equity"
        ws['B19'] = f"{valuation.get('cost_of_equity', 13.0):.1f}%"
        
        ws['A20'] = "Terminal Growth"
        ws['B20'] = f"{valuation.get('terminal_growth', 4.0):.1f}%"
        
        # Thesis Summary
        ws['A23'] = "INVESTMENT THESIS SUMMARY"
        ws['A23'].font = SECTION_FONT
        
        summary = thesis.get('summary', f"{rec} with target price")
        ws['A24'] = summary
        ws['A24'].alignment = Alignment(wrap_text=True)
        
        # Set column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 30
    
    def _create_assumptions_sheet(self, data: Dict[str, Any]):
        """Create Assumptions sheet with actual data"""
        ws = self.wb.create_sheet("Assumptions")
        
        assumptions_data = data.get('assumptions', {})
        assumptions = assumptions_data.get('assumptions', {})
        
        ws['A1'] = "FORECAST ASSUMPTIONS"
        ws['A1'].font = TITLE_FONT
        
        # Headers
        ws['A3'] = "Parameter"
        for i, year in enumerate(self.forecast_years, start=2):
            ws.cell(row=3, column=i).value = year
        self._apply_header_style(ws, 3, len(self.forecast_years) + 1)
        
        # Get assumption values
        row = 4
        assumption_items = [
            ("loan_growth_rate", "Loan Growth Rate (%)", 100),
            ("revenue_growth_rate", "Revenue Growth Rate (%)", 100),
            ("nim", "Net Interest Margin (%)", 100),
            ("ebitda_margin", "EBITDA Margin (%)", 100),
            ("casa_ratio", "CASA Ratio (%)", 100),
            ("credit_cost", "Credit Cost (%)", 100),
            ("cost_to_income", "Cost-to-Income Ratio (%)", 100),
            ("roa", "Return on Assets (%)", 100),
            ("roe", "Return on Equity (%)", 100),
            ("tax_rate", "Tax Rate (%)", 100),
        ]
        
        for key, label, multiplier in assumption_items:
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
                        cell.alignment = Alignment(horizontal='right')
                row += 1
        
        # Rationale
        row += 2
        ws.cell(row=row, column=1).value = "RATIONALE"
        ws.cell(row=row, column=1).font = SECTION_FONT
        
        rationale = assumptions_data.get('rationale', 'Assumptions based on historical trends and sector outlook')
        ws.cell(row=row+1, column=1).value = rationale
        ws.cell(row=row+1, column=1).alignment = Alignment(wrap_text=True)
        
        ws.column_dimensions['A'].width = 30
        for i in range(2, 7):
            ws.column_dimensions[get_column_letter(i)].width = 12
    
    def _create_pnl_sheet(self, data: Dict[str, Any]):
        """Create P&L sheet with actual scraped data"""
        ws = self.wb.create_sheet("P&L")
        
        ws['A1'] = "PROFIT & LOSS STATEMENT"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "(₹ Crores)"
        ws['A2'].font = Font(size=10, italic=True, color="666666")
        
        # Get actual P&L data from scraping
        historical = data.get('historical_financials', {})
        annual_pnl = historical.get('annual_pnl', {})
        
        # Get years from scraped data or use defaults
        if annual_pnl:
            years = sorted([y for y in annual_pnl.keys() if y != 'TTM'], key=lambda x: x)[-10:]
        else:
            years = self.years
        
        # Headers
        ws['A4'] = "Line Item"
        for i, year in enumerate(years, start=2):
            ws.cell(row=4, column=i).value = year
        self._apply_header_style(ws, 4, len(years) + 1)
        
        # Map scraped line items to our standard format
        line_item_mapping = {
            'Revenue +': 'Total Income',
            'Interest': 'Interest Expense', 
            'Expenses +': 'Operating Expenses',
            'Financing Profit': 'Net Interest Income',
            'Other Income +': 'Other Income',
            'Depreciation': 'Depreciation',
            'Profit before tax': 'Profit Before Tax',
            'Net Profit +': 'PAT',
            'Tax %': 'Tax Rate (%)'
        }
        
        row = 5
        
        # Get unique line items from data
        if annual_pnl and years:
            first_year_data = annual_pnl.get(years[0], {})
            line_items = list(first_year_data.keys())
            
            for item in line_items:
                # Write line item name
                ws.cell(row=row, column=1).value = item
                ws.cell(row=row, column=1).border = THIN_BORDER
                
                # Check if this is a key row
                is_key = item in ['Revenue +', 'Net Profit +', 'Profit before tax', 'Financing Profit']
                if is_key:
                    ws.cell(row=row, column=1).font = Font(bold=True)
                
                # Write values for each year
                for col_idx, year in enumerate(years, start=2):
                    year_data = annual_pnl.get(year, {})
                    value = year_data.get(item)
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        cell.number_format = '#,##0.00'
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
                    
                    if is_key:
                        cell.font = Font(bold=True, name="Consolas", size=10)
                
                row += 1
        else:
            # Fallback template
            ws.cell(row=row, column=1).value = "No P&L data available"
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, len(years) + 2):
            ws.column_dimensions[get_column_letter(i)].width = 14
    
    def _create_balance_sheet(self, data: Dict[str, Any]):
        """Create Balance Sheet with scraped data"""
        ws = self.wb.create_sheet("Balance Sheet")
        
        ws['A1'] = "BALANCE SHEET"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "(₹ Crores)"
        ws['A2'].font = Font(size=10, italic=True, color="666666")
        
        # Get actual B/S data from scraping
        historical = data.get('historical_financials', {})
        annual_bs = historical.get('annual_bs', {})
        
        # Get years from scraped data
        if annual_bs:
            years = sorted([y for y in annual_bs.keys() if y != 'TTM'], key=lambda x: x)[-10:]
        else:
            years = self.years
        
        # Headers
        ws['A4'] = "Line Item"
        for i, year in enumerate(years, start=2):
            ws.cell(row=4, column=i).value = year
        self._apply_header_style(ws, 4, len(years) + 1)
        
        row = 5
        
        if annual_bs and years:
            first_year_data = annual_bs.get(years[0], {})
            line_items = list(first_year_data.keys())
            
            for item in line_items:
                ws.cell(row=row, column=1).value = item
                ws.cell(row=row, column=1).border = THIN_BORDER
                
                is_key = 'Total' in item or 'Equity' in item
                if is_key:
                    ws.cell(row=row, column=1).font = Font(bold=True)
                
                for col_idx, year in enumerate(years, start=2):
                    year_data = annual_bs.get(year, {})
                    value = year_data.get(item)
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        cell.number_format = '#,##0.00'
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
                
                row += 1
        else:
            ws.cell(row=row, column=1).value = "No Balance Sheet data available"
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, len(years) + 2):
            ws.column_dimensions[get_column_letter(i)].width = 14
    
    def _create_quarterly_sheet(self, data: Dict[str, Any]):
        """Create Quarterly Results sheet with scraped data"""
        ws = self.wb.create_sheet("Quarterly Results")
        
        ws['A1'] = "QUARTERLY RESULTS"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = "(₹ Crores)"
        ws['A2'].font = Font(size=10, italic=True, color="666666")
        
        # Get quarterly data
        operational = data.get('operational_data', {})
        quarterly = operational.get('quarterly_results', {})
        
        if quarterly:
            quarters = sorted(quarterly.keys(), key=lambda x: x)[-12:]
        else:
            quarters = []
        
        # Headers
        ws['A4'] = "Line Item"
        for i, q in enumerate(quarters, start=2):
            ws.cell(row=4, column=i).value = q
        if quarters:
            self._apply_header_style(ws, 4, len(quarters) + 1)
        
        row = 5
        
        if quarterly and quarters:
            first_q_data = quarterly.get(quarters[0], {})
            line_items = list(first_q_data.keys())
            
            for item in line_items:
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
        else:
            ws.cell(row=row, column=1).value = "No quarterly data available"
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, len(quarters) + 2):
            ws.column_dimensions[get_column_letter(i)].width = 12
    
    def _create_ratios_sheet(self, data: Dict[str, Any]):
        """Create Key Ratios sheet with scraped data"""
        ws = self.wb.create_sheet("Key Ratios")
        
        ws['A1'] = "KEY RATIOS"
        ws['A1'].font = TITLE_FONT
        
        # Get ratios data
        historical = data.get('historical_financials', {})
        ratios = historical.get('ratios', {})
        
        if ratios:
            years = sorted([y for y in ratios.keys() if y != 'TTM'], key=lambda x: x)[-10:]
        else:
            years = []
        
        # Headers
        ws['A3'] = "Ratio"
        for i, year in enumerate(years, start=2):
            ws.cell(row=3, column=i).value = year
        if years:
            self._apply_header_style(ws, 3, len(years) + 1)
        
        row = 4
        
        if ratios and years:
            first_year_data = ratios.get(years[0], {})
            ratio_items = list(first_year_data.keys())
            
            for item in ratio_items:
                ws.cell(row=row, column=1).value = item
                ws.cell(row=row, column=1).border = THIN_BORDER
                
                for col_idx, year in enumerate(years, start=2):
                    year_data = ratios.get(year, {})
                    value = year_data.get(item)
                    
                    cell = ws.cell(row=row, column=col_idx)
                    if value is not None:
                        cell.value = value
                        # Format as percentage if it looks like one
                        if isinstance(value, (int, float)) and abs(value) < 100:
                            cell.number_format = '0.00'
                        else:
                            cell.number_format = '#,##0.00'
                    cell.border = THIN_BORDER
                    cell.font = NUMBER_FONT
                    cell.alignment = Alignment(horizontal='right')
                
                row += 1
        
        ws.column_dimensions['A'].width = 25
        for i in range(2, len(years) + 2):
            ws.column_dimensions[get_column_letter(i)].width = 12
    
    def _create_valuation_sheet(self, data: Dict[str, Any]):
        """Create Valuation sheet with actual data"""
        ws = self.wb.create_sheet("Valuation")
        
        valuation = data.get('valuation', {})
        metadata = data.get('company_metadata', {})
        
        ws['A1'] = "VALUATION"
        ws['A1'].font = TITLE_FONT
        
        # RIV Section
        ws['A3'] = "A) RESIDUAL INCOME VALUATION (RIV)"
        ws['A3'].font = SECTION_FONT
        
        riv_data = [
            ("Risk-Free Rate (Rf)", "7.0%"),
            ("Equity Risk Premium", "6.0%"),
            ("Beta", "1.0"),
            ("Cost of Equity (Ke)", f"{valuation.get('cost_of_equity', 13.0):.1f}%"),
            ("Terminal Growth Rate", f"{valuation.get('terminal_growth', 4.0):.1f}%"),
            ("", ""),
            ("Fair Value", f"₹{valuation.get('fair_value', valuation.get('target_price', 0)):,.0f}"),
        ]
        
        row = 5
        for label, value in riv_data:
            ws.cell(row=row, column=1).value = label
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=2).value = value
            ws.cell(row=row, column=2).border = THIN_BORDER
            ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
            if label == "Fair Value":
                ws.cell(row=row, column=2).font = Font(bold=True, size=12)
            row += 1
        
        # Target Price Section
        row += 2
        ws.cell(row=row, column=1).value = "B) TARGET PRICE SUMMARY"
        ws.cell(row=row, column=1).font = SECTION_FONT
        
        row += 2
        summary_data = [
            ("Current Market Price", f"₹{metadata.get('current_price', 0):,.2f}"),
            ("RIV Fair Value", f"₹{valuation.get('fair_value', valuation.get('target_price', 0)):,.0f}"),
            ("Target Price", f"₹{valuation.get('target_price', 0):,.0f}"),
            ("Upside/Downside", f"{valuation.get('upside_percent', 0):.1f}%"),
            ("Recommendation", valuation.get('recommendation', 'HOLD')),
        ]
        
        for label, value in summary_data:
            ws.cell(row=row, column=1).value = label
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=2).value = value
            ws.cell(row=row, column=2).border = THIN_BORDER
            ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
            if label in ["Target Price", "Recommendation"]:
                ws.cell(row=row, column=2).font = Font(bold=True)
            row += 1
        
        # Rationale
        row += 2
        ws.cell(row=row, column=1).value = "Rationale"
        ws.cell(row=row, column=1).font = Font(bold=True)
        row += 1
        ws.cell(row=row, column=1).value = valuation.get('rationale', 'Valuation based on RIV methodology')
        ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 20
    
    def _create_thesis_sheet(self, data: Dict[str, Any]):
        """Create Thesis sheet with full text"""
        ws = self.wb.create_sheet("Thesis")
        
        thesis = data.get('thesis', {})
        valuation = data.get('valuation', {})
        metadata = data.get('company_metadata', {})
        
        ws['A1'] = "INVESTMENT THESIS"
        ws['A1'].font = TITLE_FONT
        
        ws['A2'] = f"{metadata.get('full_name', 'Company')} ({metadata.get('ticker', '')})"
        ws['A2'].font = Font(size=14, bold=True)
        
        # Summary box
        ws['A4'] = "RECOMMENDATION"
        ws['A4'].font = SECTION_FONT
        
        rec = valuation.get('recommendation', 'HOLD')
        ws['A5'] = f"{rec} | Target: ₹{valuation.get('target_price', 0):,.0f} | Upside: {valuation.get('upside_percent', 0):.1f}%"
        ws['A5'].font = Font(size=12, bold=True)
        
        # Full thesis
        ws['A7'] = "DETAILED ANALYSIS"
        ws['A7'].font = SECTION_FONT
        
        thesis_text = thesis.get('full_text', 'Investment thesis to be generated')
        ws['A8'] = thesis_text
        ws['A8'].alignment = Alignment(wrap_text=True, vertical='top')
        
        ws.column_dimensions['A'].width = 100
        ws.row_dimensions[8].height = 400
    
    def _create_key_metrics_sheet(self, data: Dict[str, Any]):
        """Create Key Metrics summary sheet"""
        ws = self.wb.create_sheet("Key Metrics")
        
        metadata = data.get('company_metadata', {})
        assumptions = data.get('assumptions', {}).get('assumptions', {})
        valuation = data.get('valuation', {})
        
        ws['A1'] = "KEY METRICS SUMMARY"
        ws['A1'].font = TITLE_FONT
        
        # Company Info
        ws['A3'] = "COMPANY INFORMATION"
        ws['A3'].font = SECTION_FONT
        
        info_data = [
            ("Company Name", metadata.get('full_name', 'N/A')),
            ("Ticker", metadata.get('ticker', 'N/A')),
            ("Sector", metadata.get('sector', 'N/A')),
            ("Industry", metadata.get('industry', 'N/A')),
            ("Market Cap (₹ Cr)", f"{metadata.get('market_cap', 0):,.0f}"),
            ("Current Price", f"₹{metadata.get('current_price', 0):,.2f}"),
        ]
        
        row = 4
        for label, value in info_data:
            ws.cell(row=row, column=1).value = label
            ws.cell(row=row, column=2).value = value
            ws.cell(row=row, column=2).font = Font(bold=True)
            row += 1
        
        # Valuation Summary
        row += 1
        ws.cell(row=row, column=1).value = "VALUATION SUMMARY"
        ws.cell(row=row, column=1).font = SECTION_FONT
        
        row += 1
        val_data = [
            ("Recommendation", valuation.get('recommendation', 'N/A')),
            ("Target Price", f"₹{valuation.get('target_price', 0):,.0f}"),
            ("Upside", f"{valuation.get('upside_percent', 0):.1f}%"),
            ("Cost of Equity", f"{valuation.get('cost_of_equity', 13.0):.1f}%"),
            ("Terminal Growth", f"{valuation.get('terminal_growth', 4.0):.1f}%"),
        ]
        
        for label, value in val_data:
            ws.cell(row=row, column=1).value = label
            ws.cell(row=row, column=2).value = value
            ws.cell(row=row, column=2).font = Font(bold=True)
            row += 1
        
        # Key Assumptions
        row += 1
        ws.cell(row=row, column=1).value = "KEY FORECAST ASSUMPTIONS (FY26E)"
        ws.cell(row=row, column=1).font = SECTION_FONT
        
        row += 1
        for key, label in [("roe", "ROE"), ("loan_growth_rate", "Loan Growth"), ("nim", "NIM"), ("credit_cost", "Credit Cost")]:
            if key in assumptions:
                values = assumptions[key]
                val = values[0] if isinstance(values, list) and values else 0
                ws.cell(row=row, column=1).value = label
                ws.cell(row=row, column=2).value = f"{val * 100:.1f}%"
                row += 1
        
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 20
