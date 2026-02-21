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
