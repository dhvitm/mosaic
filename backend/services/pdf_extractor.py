"""
PDF Extraction Service for Investor Presentations and Annual Reports
Downloads and parses PDF files to extract key financial metrics and detailed financials
"""
import os
import re
import logging
import tempfile
import requests
import pdfplumber
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFExtractor:
    """Extract text and metrics from investor presentation and annual report PDFs"""
    
    def __init__(self):
        self.download_dir = Path("/app/temp_pdfs")
        self.download_dir.mkdir(exist_ok=True)
        
        # Common headers for downloading
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Key metrics patterns for banks
        self.bank_metric_patterns = {
            'nim': [r'NIM[:\s]+(\d+\.?\d*)\s*%', r'Net Interest Margin[:\s]+(\d+\.?\d*)\s*%'],
            'casa': [r'CASA[:\s]+(\d+\.?\d*)\s*%', r'CASA Ratio[:\s]+(\d+\.?\d*)\s*%'],
            'gnpa': [r'GNPA[:\s]+(\d+\.?\d*)\s*%', r'Gross NPA[:\s]+(\d+\.?\d*)\s*%'],
            'nnpa': [r'NNPA[:\s]+(\d+\.?\d*)\s*%', r'Net NPA[:\s]+(\d+\.?\d*)\s*%'],
            'car': [r'CAR[:\s]+(\d+\.?\d*)\s*%', r'Capital Adequacy[:\s]+(\d+\.?\d*)\s*%', r'CRAR[:\s]+(\d+\.?\d*)\s*%'],
            'roe': [r'RoE[:\s]+(\d+\.?\d*)\s*%', r'Return on Equity[:\s]+(\d+\.?\d*)\s*%'],
            'roa': [r'RoA[:\s]+(\d+\.?\d*)\s*%', r'Return on Assets[:\s]+(\d+\.?\d*)\s*%'],
            'cost_to_income': [r'Cost[- ]to[- ]Income[:\s]+(\d+\.?\d*)\s*%', r'C/I Ratio[:\s]+(\d+\.?\d*)\s*%'],
            'provision_coverage': [r'PCR[:\s]+(\d+\.?\d*)\s*%', r'Provision Coverage[:\s]+(\d+\.?\d*)\s*%'],
            'loan_growth': [r'Loan Growth[:\s]+(\d+\.?\d*)\s*%', r'Advances Growth[:\s]+(\d+\.?\d*)\s*%'],
            'deposit_growth': [r'Deposit Growth[:\s]+(\d+\.?\d*)\s*%'],
        }
        
        # P&L line items to extract from annual reports (for banks)
        self.bank_pnl_items = [
            'Interest Earned', 'Interest/Discount on Advances/Bills', 'Income on Investments',
            'Interest on Balances with RBI', 'Others',
            'Other Income', 'Commission, Exchange and Brokerage', 'Profit on Sale of Investments',
            'Profit on Sale of Land, Buildings', 'Profit on Exchange Transactions',
            'Interest Expended', 'Interest on Deposits', 'Interest on RBI/Inter-Bank Borrowings',
            'Operating Expenses', 'Payments to and Provisions for Employees', 'Employee Cost',
            'Rent, Taxes and Lighting', 'Printing and Stationery', 'Advertisement and Publicity',
            'Depreciation', 'Directors Fees', 'Auditors Fees', 'Law Charges', 'Postage, Telegram',
            'Repairs and Maintenance', 'Insurance', 'Other Expenditure',
            'Provisions and Contingencies', 'Provision for Tax', 'Provision for NPA',
            'Provision for Standard Assets', 'Provision for Depreciation on Investments',
            'Operating Profit', 'Profit Before Tax', 'Tax Expense', 'Net Profit', 'PAT'
        ]
        
        # Balance Sheet items for banks
        self.bank_bs_items = [
            'Capital', 'Share Capital', 'Equity Share Capital', 'Reserves and Surplus',
            'Statutory Reserves', 'Capital Reserves', 'Revenue Reserves', 'Balance in P&L',
            'Deposits', 'Demand Deposits', 'Savings Bank Deposits', 'Term Deposits',
            'Borrowings', 'Borrowings from RBI', 'Borrowings from Banks', 'Other Borrowings',
            'Other Liabilities and Provisions', 'Bills Payable', 'Inter-Office Adjustments',
            'Interest Accrued', 'Contingent Provisions',
            'Cash and Balances with RBI', 'Cash in Hand', 'Balances with RBI',
            'Balances with Banks', 'Money at Call and Short Notice',
            'Investments', 'Government Securities', 'Other Approved Securities',
            'Shares', 'Debentures and Bonds', 'Subsidiaries/Joint Ventures',
            'Advances', 'Bills Purchased and Discounted', 'Cash Credits and Overdrafts',
            'Term Loans', 'Fixed Assets', 'Premises', 'Other Fixed Assets',
            'Other Assets', 'Interest Accrued', 'Tax Paid in Advance', 'Stationery and Stamps',
            'Non-banking Assets', 'Deferred Tax Assets'
        ]
    
    def download_pdf(self, url: str, filename: str = None) -> Optional[str]:
        """Download PDF from URL and return local path"""
        try:
            if not filename:
                filename = f"presentation_{hash(url) % 100000}.pdf"
            
            filepath = self.download_dir / filename
            
            # Skip if already downloaded
            if filepath.exists():
                logger.info(f"PDF already exists: {filepath}")
                return str(filepath)
            
            logger.info(f"Downloading PDF from: {url[:80]}...")
            
            response = requests.get(url, headers=self.headers, timeout=30, allow_redirects=True)
            
            if response.status_code == 200:
                # Check if it's actually a PDF
                content_type = response.headers.get('content-type', '')
                if 'pdf' in content_type.lower() or url.lower().endswith('.pdf'):
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Downloaded PDF: {filepath} ({len(response.content)} bytes)")
                    return str(filepath)
                else:
                    logger.warning(f"URL did not return PDF (content-type: {content_type})")
                    return None
            else:
                logger.warning(f"Failed to download PDF: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            return None
    
    def extract_text_from_pdf(self, filepath: str, max_pages: int = 20) -> str:
        """Extract text from PDF file"""
        try:
            text_parts = []
            
            with pdfplumber.open(filepath) as pdf:
                pages_to_extract = min(len(pdf.pages), max_pages)
                
                for i, page in enumerate(pdf.pages[:pages_to_extract]):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                    
                    # Also try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            # Convert table to text
                            table_text = "\n".join([
                                " | ".join([str(cell) if cell else "" for cell in row])
                                for row in table if row
                            ])
                            if table_text.strip():
                                text_parts.append(f"[Table]\n{table_text}")
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} chars from {filepath}")
            return full_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    def extract_metrics_from_text(self, text: str, is_bank: bool = True) -> Dict[str, Any]:
        """Extract financial metrics from text using regex patterns"""
        metrics = {}
        
        # Choose patterns based on company type
        patterns = self.bank_metric_patterns if is_bank else self.general_metric_patterns
        
        for metric_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1).replace(',', ''))
                        metrics[metric_name] = value
                        break  # Found a match, move to next metric
                    except (ValueError, IndexError):
                        continue
        
        # Also extract any guidance or outlook statements
        guidance_patterns = [
            r'guidance[:\s]+([^.]+\.)',
            r'expect[s]?.*?(\d+[\d,-]*%?\s*(?:growth|increase|improvement))',
            r'target[s]?.*?(\d+[\d,-]*%?\s*(?:growth|ROE|NIM|CASA))',
            r'outlook[:\s]+([^.]+\.)',
        ]
        
        guidance_statements = []
        for pattern in guidance_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:3]:  # Limit to 3 per pattern
                if len(match) > 20:  # Skip very short matches
                    guidance_statements.append(match.strip())
        
        if guidance_statements:
            metrics['guidance'] = guidance_statements[:5]  # Limit to 5 total
        
        return metrics
    
    async def extract_metrics_with_ai(self, text: str, claude_service, is_bank: bool = True) -> Dict[str, Any]:
        """Use Claude AI to extract structured metrics from presentation text"""
        try:
            # Limit text to avoid token limits
            truncated_text = text[:15000] if len(text) > 15000 else text
            
            if is_bank:
                system_prompt = """You are a financial analyst expert. Extract key banking metrics from investor presentation text.
Return ONLY a JSON object with the following structure (omit keys if data not found):
{
  "nim": float (Net Interest Margin %),
  "casa": float (CASA Ratio %),
  "gnpa": float (Gross NPA %),
  "nnpa": float (Net NPA %),
  "car": float (Capital Adequacy Ratio %),
  "roe": float (Return on Equity %),
  "roa": float (Return on Assets %),
  "cost_to_income": float (%),
  "loan_growth": float (YoY %),
  "deposit_growth": float (YoY %),
  "provision_coverage": float (PCR %),
  "slippage_ratio": float (%),
  "guidance": [list of management guidance statements],
  "key_highlights": [list of 3-5 key operational highlights]
}"""
            else:
                system_prompt = """You are a financial analyst expert. Extract key financial metrics from investor presentation text.
Return ONLY a JSON object with the following structure (omit keys if data not found):
{
  "revenue_growth": float (YoY %),
  "ebitda_margin": float (%),
  "pat_margin": float (%),
  "pat_growth": float (YoY %),
  "capex": float (Rs. Crores),
  "debt_equity": float (ratio),
  "roce": float (%),
  "roe": float (%),
  "guidance": [list of management guidance statements],
  "key_highlights": [list of 3-5 key operational highlights]
}"""

            user_prompt = f"""Extract financial metrics from this investor presentation text:

{truncated_text}

Return ONLY valid JSON, no explanation."""

            response = await claude_service.call_claude(system_prompt, user_prompt, "pdf_extraction")
            
            # Parse JSON from response
            import json
            
            # Try to find JSON in response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                metrics = json.loads(json_match.group())
                return metrics
            
            # Try parsing the whole response
            metrics = json.loads(response)
            return metrics
            
        except Exception as e:
            logger.error(f"AI extraction failed: {str(e)}")
            return {}
    
    async def process_presentations(self, presentations: List[Dict], claude_service, 
                                   is_bank: bool = True, max_pdfs: int = 3) -> Dict[str, Any]:
        """Process multiple presentations and aggregate metrics"""
        all_metrics = {
            'extracted_from_pdfs': 0,
            'quarters_processed': [],
            'metrics': {},
            'guidance': [],
            'key_highlights': [],
            'raw_text_sample': ''
        }
        
        processed = 0
        
        for pres in presentations[:max_pdfs]:
            url = pres.get('url', '')
            quarter = pres.get('quarter', 'Unknown')
            
            if not url or not url.endswith('.pdf'):
                continue
            
            try:
                # Download PDF
                filepath = self.download_pdf(url, f"pres_{quarter.replace(' ', '_')}.pdf")
                if not filepath:
                    continue
                
                # Extract text
                text = self.extract_text_from_pdf(filepath)
                if not text:
                    continue
                
                # Store sample of raw text
                if not all_metrics['raw_text_sample']:
                    all_metrics['raw_text_sample'] = text[:3000]
                
                # Extract metrics using regex first (faster)
                regex_metrics = self.extract_metrics_from_text(text, is_bank)
                
                # Use AI extraction for more comprehensive parsing
                ai_metrics = await self.extract_metrics_with_ai(text, claude_service, is_bank)
                
                # Merge metrics (AI takes precedence)
                combined_metrics = {**regex_metrics, **ai_metrics}
                
                # Store by quarter
                all_metrics['quarters_processed'].append(quarter)
                all_metrics['metrics'][quarter] = combined_metrics
                
                # Aggregate guidance
                if 'guidance' in combined_metrics:
                    for g in combined_metrics['guidance']:
                        if g not in all_metrics['guidance']:
                            all_metrics['guidance'].append(g)
                
                # Aggregate highlights
                if 'key_highlights' in combined_metrics:
                    for h in combined_metrics['key_highlights']:
                        if h not in all_metrics['key_highlights']:
                            all_metrics['key_highlights'].append(h)
                
                processed += 1
                logger.info(f"Processed presentation for {quarter}: {len(combined_metrics)} metrics")
                
                # Clean up downloaded file
                try:
                    os.remove(filepath)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Error processing presentation {quarter}: {str(e)}")
                continue
        
        all_metrics['extracted_from_pdfs'] = processed
        
        # Create a summary of latest metrics
        if all_metrics['metrics']:
            latest_quarter = all_metrics['quarters_processed'][0] if all_metrics['quarters_processed'] else None
            if latest_quarter:
                all_metrics['latest_metrics'] = all_metrics['metrics'].get(latest_quarter, {})
        
        return all_metrics
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            if self.download_dir.exists():
                shutil.rmtree(self.download_dir)
                self.download_dir.mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")


# Singleton instance
pdf_extractor = PDFExtractor()
