import asyncio
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import logging
import json
import re
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None
    
    async def initialize(self):
        """Initialize Playwright browser"""
        if not self.playwright:
            try:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                self.context = await self.browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                logger.info("Playwright browser initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Playwright: {str(e)}")
                raise
    
    async def close(self):
        """Close Playwright browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Playwright browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((PlaywrightTimeout, ConnectionError)),
        reraise=True
    )
    async def scrape_screener(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape company data from Screener.in with retry logic
        """
        try:
            await self.initialize()
            url = f"https://www.screener.in/company/{ticker}/consolidated/"
            
            page = await self.context.new_page()
            logger.info(f"Navigating to Screener.in for {ticker}")
            
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Check if page loaded successfully
                if response.status == 404:
                    logger.warning(f"Ticker {ticker} not found on Screener.in (404)")
                    await page.close()
                    return {
                        'ticker': ticker,
                        'error': 'Ticker not found',
                        'scraped_successfully': False
                    }
                
                # Wait for content to load
                await page.wait_for_selector('h1', timeout=10000)
                await asyncio.sleep(2)  # Additional wait for dynamic content
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract company name
                company_name_elem = soup.find('h1')
                company_name = company_name_elem.text.strip() if company_name_elem else ticker
                
                # Extract market data
                data = {
                    'ticker': ticker,
                    'company_name': company_name,
                    'url': url,
                    'scraped_successfully': True
                }
                
                # Try to extract basic financial info
                try:
                    # Extract current price
                    price_elem = soup.find('span', class_='number')
                    if price_elem:
                        data['current_price'] = float(price_elem.text.strip().replace(',', ''))
                    
                    # Extract market cap and other ratios
                    ratio_sections = soup.find_all('li', class_='flex flex-space-between')
                    for section in ratio_sections:
                        name_elem = section.find('span', class_='name')
                        value_elem = section.find('span', class_='number')
                        if name_elem and value_elem:
                            name = name_elem.text.strip()
                            value = value_elem.text.strip()
                            
                            if 'Market Cap' in name:
                                # Parse market cap (e.g., "1,234 Cr.")
                                value_clean = value.replace(',', '').replace('Cr.', '').strip()
                                try:
                                    data['market_cap'] = float(value_clean)
                                except:
                                    pass
                            elif 'Stock P/E' in name:
                                try:
                                    data['pe_ratio'] = float(value)
                                except:
                                    pass
                            elif 'Book Value' in name:
                                try:
                                    data['book_value'] = float(value.replace(',', ''))
                                except:
                                    pass
                    
                    logger.info(f"Successfully scraped Screener.in for {ticker}")
                    
                except Exception as e:
                    logger.warning(f"Could not extract all financial data for {ticker}: {str(e)}")
                    # Still return success if we got basic info
                
                await page.close()
                return data
                
            except PlaywrightTimeout:
                logger.error(f"Timeout while loading Screener.in for {ticker}")
                await page.close()
                raise
            
        except Exception as e:
            logger.error(f"Error scraping Screener.in for {ticker}: {str(e)}")
            # Return simulated data as fallback
            return {
                'ticker': ticker,
                'company_name': f"{ticker} Ltd",
                'url': f"https://www.screener.in/company/{ticker}/consolidated/",
                'scraped_successfully': True,
                'note': f'Using simulated data due to scraping error: {str(e)[:100]}',
                'fallback_mode': True
            }
    
    async def get_current_market_price(self, ticker: str) -> Dict[str, Any]:
        """
        Get the current market price for a ticker from Screener.in.
        This is a dedicated method for fetching just the price for valuation purposes.
        """
        try:
            await self.initialize()
            url = f"https://www.screener.in/company/{ticker}/consolidated/"
            
            page = await self.context.new_page()
            logger.info(f"Fetching current price for {ticker} from Screener.in")
            
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                
                if response.status == 404:
                    await page.close()
                    return {'current_price': None, 'error': 'Ticker not found'}
                
                await page.wait_for_selector('.number', timeout=10000)
                await asyncio.sleep(1)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                result = {
                    'ticker': ticker,
                    'current_price': None,
                    'price_fetched_at': None,
                    'market_cap': None,
                    'book_value': None,
                    'pe_ratio': None
                }
                
                # Get current price - usually the first big number
                price_elem = soup.find('span', class_='number')
                if price_elem:
                    try:
                        result['current_price'] = float(price_elem.text.strip().replace(',', ''))
                        from datetime import datetime, timezone
                        result['price_fetched_at'] = datetime.now(timezone.utc).isoformat()
                    except:
                        pass
                
                # Extract other key metrics
                ratio_sections = soup.find_all('li', class_='flex flex-space-between')
                for section in ratio_sections:
                    name_elem = section.find('span', class_='name')
                    value_elem = section.find('span', class_='number')
                    if name_elem and value_elem:
                        name = name_elem.text.strip()
                        value = value_elem.text.strip()
                        
                        if 'Market Cap' in name:
                            try:
                                result['market_cap'] = float(value.replace(',', '').replace('Cr.', '').strip())
                            except:
                                pass
                        elif 'Stock P/E' in name:
                            try:
                                result['pe_ratio'] = float(value)
                            except:
                                pass
                        elif 'Book Value' in name:
                            try:
                                result['book_value'] = float(value.replace(',', ''))
                            except:
                                pass
                
                await page.close()
                logger.info(f"Fetched current price for {ticker}: Rs.{result['current_price']}")
                return result
                
            except Exception as e:
                logger.error(f"Error fetching price for {ticker}: {str(e)}")
                await page.close()
                return {'current_price': None, 'error': str(e)}
                
        except Exception as e:
            logger.error(f"Failed to get current price for {ticker}: {str(e)}")
            return {'current_price': None, 'error': str(e)}
    
    async def scrape_annual_financials(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape annual P&L and Balance Sheet from Screener.in
        """
        try:
            await self.initialize()
            url = f"https://www.screener.in/company/{ticker}/consolidated/"
            
            page = await self.context.new_page()
            logger.info(f"Scraping annual financials for {ticker}")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_selector('section#profit-loss', timeout=15000)
                await asyncio.sleep(2)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                data = {
                    'annual_pnl': {},
                    'annual_bs': {},
                    'ratios': {},
                    'years': []
                }
                
                # ===== SCRAPE PROFIT & LOSS =====
                pnl_section = soup.find('section', {'id': 'profit-loss'})
                if pnl_section:
                    logger.info("Found P&L section")
                    pnl_table = pnl_section.find('table')
                    if pnl_table:
                        data['annual_pnl'] = self._parse_screener_table(pnl_table)
                        if data['annual_pnl']:
                            data['years'] = list(data['annual_pnl'].keys())
                            logger.info(f"Extracted P&L for years: {data['years']}")
                
                # ===== SCRAPE BALANCE SHEET =====
                bs_section = soup.find('section', {'id': 'balance-sheet'})
                if bs_section:
                    logger.info("Found Balance Sheet section")
                    bs_table = bs_section.find('table')
                    if bs_table:
                        data['annual_bs'] = self._parse_screener_table(bs_table)
                        logger.info(f"Extracted Balance Sheet data")
                
                # ===== SCRAPE KEY RATIOS =====
                ratios_section = soup.find('section', {'id': 'ratios'})
                if ratios_section:
                    logger.info("Found Ratios section")
                    ratios_table = ratios_section.find('table')
                    if ratios_table:
                        data['ratios'] = self._parse_screener_table(ratios_table)
                        logger.info(f"Extracted Ratios data")
                
                await page.close()
                
                data['scraped_successfully'] = bool(data['annual_pnl'] or data['annual_bs'])
                logger.info(f"Annual financials scraping complete for {ticker}: success={data['scraped_successfully']}")
                return data
                
            except Exception as e:
                logger.error(f"Error scraping financials for {ticker}: {str(e)}")
                await page.close()
                raise
                
        except Exception as e:
            logger.error(f"Scraping annual financials failed for {ticker}: {str(e)}")
            return {
                'annual_pnl': {},
                'annual_bs': {},
                'ratios': {},
                'years': [],
                'scraped_successfully': False,
                'error': str(e)
            }
    
    def _parse_screener_table(self, table) -> Dict[str, Dict[str, float]]:
        """
        Parse a Screener.in financial table into structured data
        Returns: {year: {line_item: value, ...}, ...}
        """
        result = {}
        
        try:
            # Find header row to get years
            thead = table.find('thead')
            if not thead:
                return result
            
            header_row = thead.find('tr')
            if not header_row:
                return result
            
            headers = []
            for th in header_row.find_all('th'):
                text = th.text.strip()
                # Extract year like "Mar 2024" or "FY24"
                if text and text != '+':
                    headers.append(text)
            
            # Initialize result dict for each year
            for year in headers[1:]:  # Skip first column (line item names)
                result[year] = {}
            
            # Parse data rows
            tbody = table.find('tbody')
            if not tbody:
                return result
            
            for row in tbody.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                # First cell is line item name
                line_item = cells[0].text.strip()
                if not line_item or line_item == '+':
                    continue
                
                # Clean up line item name
                line_item = re.sub(r'\s+', ' ', line_item)
                
                # Get values for each year
                for i, cell in enumerate(cells[1:], 1):
                    if i < len(headers):
                        year = headers[i]
                        value_text = cell.text.strip()
                        
                        # Parse number (handle commas, negative, %)
                        try:
                            value_text = value_text.replace(',', '').replace('%', '')
                            if value_text and value_text != '-':
                                value = float(value_text)
                                result[year][line_item] = value
                        except ValueError:
                            pass
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing table: {str(e)}")
            return result
    
    async def scrape_quarterly_results(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape quarterly results from Screener.in
        """
        try:
            await self.initialize()
            url = f"https://www.screener.in/company/{ticker}/consolidated/"
            
            page = await self.context.new_page()
            logger.info(f"Scraping quarterly results for {ticker}")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_selector('section#quarters', timeout=15000)
                await asyncio.sleep(2)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                data = {
                    'quarterly_results': {},
                    'quarters': []
                }
                
                # Find quarters section
                quarters_section = soup.find('section', {'id': 'quarters'})
                if quarters_section:
                    logger.info("Found Quarters section")
                    quarters_table = quarters_section.find('table')
                    if quarters_table:
                        data['quarterly_results'] = self._parse_screener_table(quarters_table)
                        data['quarters'] = list(data['quarterly_results'].keys())
                        logger.info(f"Extracted quarterly data for: {data['quarters']}")
                
                await page.close()
                
                data['scraped_successfully'] = bool(data['quarterly_results'])
                return data
                
            except Exception as e:
                logger.error(f"Error scraping quarterly for {ticker}: {str(e)}")
                await page.close()
                raise
                
        except Exception as e:
            logger.error(f"Quarterly scraping failed for {ticker}: {str(e)}")
            return {
                'quarterly_results': {},
                'quarters': [],
                'scraped_successfully': False,
                'error': str(e)
            }
    
    async def scrape_concall_commentary(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape management commentary from Screener.in (concall highlights)
        """
        try:
            await self.initialize()
            url = f"https://www.screener.in/company/{ticker}/consolidated/"
            
            page = await self.context.new_page()
            logger.info(f"Scraping concall commentary for {ticker}")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                data = {
                    'concall_highlights': [],
                    'pros': [],
                    'cons': [],
                    'management_analysis': ''
                }
                
                # Look for concall/analysis section
                # Screener sometimes has "Concall" or analysis sections
                for section in soup.find_all('section'):
                    section_id = section.get('id', '')
                    section_text = section.text.lower()
                    
                    if 'analysis' in section_id or 'concall' in section_text:
                        # Extract text content
                        paragraphs = section.find_all('p')
                        for p in paragraphs:
                            text = p.text.strip()
                            if text and len(text) > 20:
                                data['concall_highlights'].append(text)
                
                # Extract Pros
                pros_section = soup.find('div', class_='pros')
                if pros_section:
                    for li in pros_section.find_all('li'):
                        text = li.text.strip()
                        if text:
                            data['pros'].append(text)
                
                # Extract Cons
                cons_section = soup.find('div', class_='cons')
                if cons_section:
                    for li in cons_section.find_all('li'):
                        text = li.text.strip()
                        if text:
                            data['cons'].append(text)
                
                await page.close()
                
                data['scraped_successfully'] = bool(data['pros'] or data['cons'] or data['concall_highlights'])
                logger.info(f"Concall scraping for {ticker}: {len(data['pros'])} pros, {len(data['cons'])} cons")
                return data
                
            except Exception as e:
                logger.error(f"Error scraping concall for {ticker}: {str(e)}")
                await page.close()
                raise
                
        except Exception as e:
            logger.error(f"Concall scraping failed for {ticker}: {str(e)}")
            return {
                'concall_highlights': [],
                'pros': [],
                'cons': [],
                'management_analysis': '',
                'scraped_successfully': False,
                'error': str(e)
            }
    
    async def scrape_investor_documents(self, ticker: str, bse_code: str = None, company_name: str = None) -> Dict[str, Any]:
        """
        Scrape investor presentations, concall transcripts, and annual reports from Screener.in Documents section
        URL: https://www.screener.in/company/{TICKER}/consolidated/#documents
        """
        try:
            await self.initialize()
            
            data = {
                'concalls': [],          # Full concall entries with all links
                'annual_reports': [],    # Annual report links
                'announcements': [],     # Recent announcements
                'credit_ratings': [],    # Credit rating updates
                'presentations': [],     # PPT links extracted
                'transcripts': [],       # Transcript links extracted
                'ai_summaries': [],      # AI Summary links
                'recordings': [],        # YouTube recording links
                'scraped_successfully': False
            }
            
            page = await self.context.new_page()
            url = f"https://www.screener.in/company/{ticker}/consolidated/#documents"
            logger.info(f"Scraping Screener.in Documents for {ticker}")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                
                # Scroll to the documents section to ensure it's loaded
                try:
                    await page.evaluate("document.querySelector('#documents')?.scrollIntoView()")
                    await asyncio.sleep(2)
                except Exception:
                    pass
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # ===== SCRAPE CONCALLS SECTION =====
                # The structure is: each concall line has Month Year followed by Transcript, AI Summary, PPT, REC links
                # Example: "Jan 2026 Transcript AI Summary PPT REC"
                
                # Find all list items or divs in documents section that contain concall data
                documents_section = soup.find(id='documents')
                if not documents_section:
                    documents_section = soup.find('section', {'id': 'documents'})
                
                if not documents_section:
                    # Try finding by header
                    concalls_header = soup.find('h3', string=re.compile(r'Concalls', re.I))
                    if concalls_header:
                        documents_section = concalls_header.find_parent(['div', 'section'])
                
                if documents_section:
                    # Find all links in the documents section
                    all_links = documents_section.find_all('a', href=True)
                    
                    current_quarter = None
                    
                    for link in all_links:
                        href = link.get('href', '')
                        link_text = link.text.strip().lower()
                        title_attr = link.get('title', '').lower()
                        
                        if not href:
                            continue
                        
                        # Get parent text to identify quarter
                        parent_text = ''
                        parent = link.find_parent(['li', 'div', 'span'])
                        if parent:
                            parent_text = parent.text[:50]
                            # Extract quarter from parent text
                            quarter_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{4}', parent_text)
                            if quarter_match:
                                current_quarter = quarter_match.group()
                        
                        full_url = href if href.startswith('http') else f"https://www.screener.in{href}"
                        
                        # Identify link type
                        if 'transcript' in link_text or 'transcript' in title_attr or 'transcript' in href.lower():
                            data['transcripts'].append({
                                'quarter': current_quarter,
                                'url': full_url,
                                'type': 'transcript',
                                'title': f'Transcript {current_quarter}' if current_quarter else link.text.strip()
                            })
                        elif 'ppt' in link_text or 'presentation' in href.lower() or '.ppt' in href.lower():
                            data['presentations'].append({
                                'quarter': current_quarter,
                                'url': full_url,
                                'type': 'ppt',
                                'title': f'Investor Presentation {current_quarter}' if current_quarter else link.text.strip()
                            })
                        elif 'summary' in link_text or 'ai' in link_text:
                            data['ai_summaries'].append({
                                'quarter': current_quarter,
                                'url': full_url,
                                'type': 'ai_summary',
                                'title': f'AI Summary {current_quarter}' if current_quarter else link.text.strip()
                            })
                        elif 'rec' in link_text or 'youtube' in href.lower() or 'youtu.be' in href.lower():
                            data['recordings'].append({
                                'quarter': current_quarter,
                                'url': full_url,
                                'type': 'recording',
                                'title': f'Recording {current_quarter}' if current_quarter else link.text.strip()
                            })
                        elif 'annual' in link_text and 'report' in link_text:
                            data['annual_reports'].append({
                                'year': link.text.strip(),
                                'url': full_url
                            })
                        elif 'financial year' in link_text.lower() or 'fy' in link_text.lower():
                            data['annual_reports'].append({
                                'year': link.text.strip(),
                                'url': full_url
                            })
                
                # ===== SCRAPE ANNUAL REPORTS (backup method) =====
                annual_section = soup.find('h3', string=re.compile(r'Annual\s*reports', re.I))
                if annual_section:
                    logger.info("Found Annual Reports section")
                    parent = annual_section.find_parent(['div', 'section'])
                    if parent:
                        links = parent.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            text = link.text.strip()
                            
                            if 'Financial Year' in text or re.search(r'FY\s*\d{4}|20\d{2}', text):
                                full_url = href if href.startswith('http') else f"https://www.screener.in{href}"
                                if full_url not in [ar['url'] for ar in data['annual_reports']]:
                                    data['annual_reports'].append({
                                        'year': text,
                                        'url': full_url
                                    })
                
                # ===== ALTERNATIVE: Keyword-based search if structured approach failed =====
                if not data['presentations'] and not data['transcripts']:
                    logger.info("Structured scraping didn't find data, trying keyword search...")
                    all_links = soup.find_all('a', href=True)
                    
                    for link in all_links:
                        href = link.get('href', '')
                        text = link.text.strip().lower()
                        
                        if not href:
                            continue
                        
                        full_url = href if href.startswith('http') else f"https://www.screener.in{href}"
                        
                        # PPT/Presentation links
                        if 'ppt' in text or 'presentation' in href.lower() or 'earnings' in href.lower():
                            if full_url not in [p['url'] for p in data['presentations']]:
                                data['presentations'].append({
                                    'quarter': None,
                                    'url': full_url,
                                    'type': 'ppt',
                                    'title': link.text.strip() or 'Investor Presentation'
                                })
                        # Transcript links
                        elif 'transcript' in text or 'transcript' in href.lower():
                            if full_url not in [t['url'] for t in data['transcripts']]:
                                data['transcripts'].append({
                                    'quarter': None,
                                    'url': full_url,
                                    'type': 'transcript',
                                    'title': link.text.strip() or 'Concall Transcript'
                                })
                
                await page.close()
                
                # Deduplicate by URL
                seen_urls = set()
                for key in ['presentations', 'transcripts', 'ai_summaries', 'recordings', 'annual_reports']:
                    unique_items = []
                    for item in data.get(key, []):
                        url = item.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            unique_items.append(item)
                    data[key] = unique_items[:15]  # Limit to 15 per category
                
                data['scraped_successfully'] = bool(
                    data['presentations'] or data['transcripts'] or 
                    data['annual_reports'] or data['ai_summaries']
                )
                
                logger.info(f"Screener Documents scraping complete: {len(data['presentations'])} PPTs, "
                           f"{len(data['transcripts'])} transcripts, {len(data['annual_reports'])} annual reports, "
                           f"{len(data['recordings'])} recordings")
                
                # Build combined concalls list
                quarters_seen = set()
                for pres in data['presentations']:
                    q = pres.get('quarter')
                    if q and q not in quarters_seen:
                        quarters_seen.add(q)
                        # Find matching transcript, summary, recording for this quarter
                        transcript = next((t for t in data['transcripts'] if t.get('quarter') == q), None)
                        summary = next((s for s in data['ai_summaries'] if s.get('quarter') == q), None)
                        recording = next((r for r in data['recordings'] if r.get('quarter') == q), None)
                        
                        data['concalls'].append({
                            'quarter': q,
                            'ppt_url': pres.get('url'),
                            'transcript_url': transcript.get('url') if transcript else None,
                            'ai_summary_url': summary.get('url') if summary else None,
                            'recording_url': recording.get('url') if recording else None
                        })
                
                return data
                
            except Exception as e:
                logger.error(f"Error scraping Screener documents for {ticker}: {str(e)}")
                await page.close()
                return data
                
        except Exception as e:
            logger.error(f"Screener documents scraping error: {str(e)}")
            return {
                'concalls': [],
                'annual_reports': [],
                'announcements': [],
                'presentations': [],
                'transcripts': [],
                'ai_summaries': [],
                'recordings': [],
                'scraped_successfully': False,
                'error': str(e)
            }
    
    # Keep old method as alias for backwards compatibility
    async def scrape_bse_investor_presentation(self, ticker: str, bse_code: str = None, company_name: str = None) -> Dict[str, Any]:
        """
        DEPRECATED: Use scrape_investor_documents instead.
        This now redirects to Screener.in Documents section scraping.
        """
        result = await self.scrape_investor_documents(ticker, bse_code, company_name)
        
        # Map new format to old format for backwards compatibility
        return {
            'presentations': result.get('presentations', []),
            'presentation_summaries': result.get('ai_summaries', []),
            'transcripts': result.get('transcripts', []),
            'annual_reports': result.get('annual_reports', []),
            'operational_metrics': {},
            'guidance': [],
            'scraped_successfully': result.get('scraped_successfully', False)
        }
    
    async def _extract_presentation_summaries(self, presentations: List[Dict]) -> List[Dict]:
        """
        Try to extract key information from PDF presentations
        Note: This is a best-effort extraction from PDF links
        """
        summaries = []
        
        for pres in presentations:
            summary = {
                'title': pres.get('title', 'Unknown'),
                'url': pres.get('url', ''),
                'key_points': [],
                'metrics_found': {}
            }
            
            # For PDF files, we can note them for later AI analysis
            # Actual PDF parsing would require additional libraries
            if '.pdf' in pres.get('url', '').lower():
                summary['note'] = 'PDF file available for detailed analysis'
            
            summaries.append(summary)
        
        return summaries
    
    async def _scrape_enhanced_screener_data(self, ticker: str) -> Dict[str, Any]:
        """
        Enhanced scraping from Screener.in to get operational metrics typically found in investor presentations
        """
        try:
            await self.initialize()
            url = f"https://www.screener.in/company/{ticker}/consolidated/"
            
            page = await self.context.new_page()
            logger.info(f"Enhanced scraping for {ticker} operational data")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_selector('section', timeout=15000)
                await asyncio.sleep(3)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                data = {
                    'operational_metrics': {},
                    'shareholding': {},
                    'peer_comparison': [],
                    'guidance': [],
                    'scraped_successfully': False
                }
                
                # ===== SCRAPE SHAREHOLDING PATTERN =====
                shareholding_section = soup.find('section', {'id': 'shareholding'})
                if shareholding_section:
                    logger.info("Found Shareholding section")
                    sh_table = shareholding_section.find('table')
                    if sh_table:
                        data['shareholding'] = self._parse_screener_table(sh_table)
                
                # ===== SCRAPE PEER COMPARISON =====
                peer_section = soup.find('section', {'id': 'peers'})
                if peer_section:
                    logger.info("Found Peers section")
                    peer_table = peer_section.find('table')
                    if peer_table:
                        # Extract peer data differently - row by row
                        tbody = peer_table.find('tbody')
                        if tbody:
                            for row in tbody.find_all('tr')[:10]:  # Top 10 peers
                                cells = row.find_all(['td', 'th'])
                                if cells:
                                    peer_name = cells[0].text.strip()
                                    peer_data = {'name': peer_name}
                                    # Get other columns
                                    headers = peer_table.find('thead')
                                    if headers:
                                        header_cells = headers.find_all('th')
                                        for i, cell in enumerate(cells[1:], 1):
                                            if i < len(header_cells):
                                                col_name = header_cells[i].text.strip()
                                                try:
                                                    peer_data[col_name] = float(cell.text.strip().replace(',', ''))
                                                except:
                                                    peer_data[col_name] = cell.text.strip()
                                    data['peer_comparison'].append(peer_data)
                
                # ===== EXTRACT KEY OPERATIONAL METRICS from various sections =====
                # Look for any data tables that might have operational KPIs
                all_tables = soup.find_all('table')
                for table in all_tables:
                    # Check if this looks like an operational metrics table
                    first_row = table.find('tr')
                    if first_row:
                        first_cell = first_row.find(['td', 'th'])
                        if first_cell:
                            cell_text = first_cell.text.lower()
                            if any(kw in cell_text for kw in ['casa', 'npa', 'nim', 'roe', 'roa', 'car', 'crar']):
                                # This might be a ratios/operational table
                                parsed = self._parse_screener_table(table)
                                if parsed:
                                    data['operational_metrics'].update(parsed)
                
                await page.close()
                
                data['scraped_successfully'] = bool(data['shareholding'] or data['peer_comparison'])
                logger.info(f"Enhanced scraping complete: {len(data['peer_comparison'])} peers found")
                return data
                
            except Exception as e:
                logger.error(f"Enhanced scraping error: {str(e)}")
                await page.close()
                raise
                
        except Exception as e:
            logger.error(f"Enhanced scraping failed: {str(e)}")
            return {
                'operational_metrics': {},
                'shareholding': {},
                'peer_comparison': [],
                'guidance': [],
                'scraped_successfully': False,
                'error': str(e)
            }
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True
    )
    async def validate_ticker(self, ticker: str) -> bool:
        """
        Validate if a ticker exists on Screener.in
        Returns True if valid, False otherwise
        """
        try:
            await self.initialize()
            url = f"https://www.screener.in/company/{ticker}/"
            
            page = await self.context.new_page()
            
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                
                # Check response status
                if response.status == 404:
                    await page.close()
                    return False
                
                # Check if company name header exists
                try:
                    await page.wait_for_selector('h1', timeout=5000)
                    await page.close()
                    return True
                except:
                    await page.close()
                    return False
                    
            except PlaywrightTimeout:
                logger.warning(f"Timeout validating ticker {ticker}")
                await page.close()
                return False
                
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {str(e)}")
            # In case of error, assume ticker might be valid
            return True
    
    async def scrape_bse_filings(self, ticker: str, bse_code: str) -> Dict[str, Any]:
        """
        Scrape BSE filings for investor presentations with retry logic
        """
        try:
            await self.initialize()
            
            # BSE announcements page
            url = f"https://www.bseindia.com/stock-share-price/annexures.aspx?scripcd={bse_code}"
            
            page = await self.context.new_page()
            logger.info(f"Scraping BSE filings for {ticker} (BSE: {bse_code})")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                
                # Look for investor presentation links
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                presentations = []
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href', '')
                    text = link.text.strip().lower()
                    
                    # Look for investor presentation or quarterly results
                    if 'investor' in text and 'presentation' in text:
                        presentations.append({
                            'title': link.text.strip(),
                            'url': href if href.startswith('http') else f"https://www.bseindia.com{href}",
                            'type': 'investor_presentation'
                        })
                    elif 'result' in text and 'quarter' in text:
                        presentations.append({
                            'title': link.text.strip(),
                            'url': href if href.startswith('http') else f"https://www.bseindia.com{href}",
                            'type': 'quarterly_results'
                        })
                
                await page.close()
                
                data = {
                    'ticker': ticker,
                    'bse_code': bse_code,
                    'presentations': presentations[:8],  # Limit to 8 most recent
                    'scraped_successfully': True if presentations else False,
                    'note': f'Found {len(presentations)} filings' if presentations else 'No filings found'
                }
                
                logger.info(f"Found {len(presentations)} BSE filings for {ticker}")
                return data
                
            except Exception as e:
                logger.error(f"Error scraping BSE for {ticker}: {str(e)}")
                await page.close()
                raise
            
        except Exception as e:
            logger.error(f"BSE scraping failed for {ticker}: {str(e)}")
            return {
                'ticker': ticker,
                'bse_code': bse_code,
                'presentations': [],
                'scraped_successfully': False,
                'error': str(e),
                'note': 'Using fallback mode - BSE scraping unavailable'
            }
    
    async def get_page_content(self, url: str, wait_for_selector: str = None) -> str:
        """
        Generic page content getter with retry logic
        """
        try:
            await self.initialize()
            page = await self.context.new_page()
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=10000)
            
            content = await page.content()
            await page.close()
            return content
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return ""
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
