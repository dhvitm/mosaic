import asyncio
import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from pathlib import Path
import sys
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

sys.path.append(str(Path(__file__).parent.parent))

from models import ModelJob, PipelineStep
from services.claude_service import ClaudeService
from services.scraper_service import ScraperService
from services.excel_generator import ExcelGenerator
from services.websocket_manager import ws_manager
from services.cache_service import CacheService
from services.pdf_extractor import pdf_extractor

logger = logging.getLogger(__name__)

# Check if agentic mode is enabled
AGENTIC_MODE = os.environ.get("MOSAIC_AGENTIC_MODE", "true").lower() == "true"

class PipelineManager:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.claude = ClaudeService()
        self.scraper = ScraperService()
        self.excel_gen = ExcelGenerator()
        self.pdf_extractor = pdf_extractor
        
        # Initialize agentic mode if enabled
        if AGENTIC_MODE:
            try:
                from services.mosaic_agent import MosaicAgent
                self.agent = MosaicAgent(self.scraper, self.pdf_extractor, self.excel_gen, db)
                logger.info("Mosaic Agent initialized - agentic mode enabled")
            except Exception as e:
                logger.error(f"Failed to initialize Mosaic Agent: {e}")
                self.agent = None
        else:
            self.agent = None
    
    async def run_pipeline(self, job_id: str, ticker: str):
        """
        Run the complete pipeline for a ticker.
        Uses agentic mode if enabled, otherwise falls back to sequential pipeline.
        """
        try:
            logger.info(f"Starting pipeline for job {job_id}, ticker {ticker}")
            
            # Check if agentic mode is available and enabled
            if AGENTIC_MODE and self.agent:
                await self._run_agentic_pipeline(job_id, ticker)
            else:
                await self._run_sequential_pipeline(job_id, ticker)
                
        except Exception as e:
            logger.error(f"Pipeline failed for job {job_id}: {str(e)}")
            await self._handle_pipeline_error(job_id, str(e))
            raise
    
    async def _run_agentic_pipeline(self, job_id: str, ticker: str):
        """Run the agentic Claude loop to build the financial model"""
        logger.info(f"Running AGENTIC pipeline for {ticker}")
        
        # Update job status (using 'id' field to match routes/generate.py)
        await self.db.model_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "processing",
                "current_step": 1,
                "mode": "agentic",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        # Broadcast start
        await ws_manager.send_activity(
            job_id, "info", 
            f"🤖 Starting autonomous analysis of {ticker} using Mosaic Agent"
        )
        
        # Run the agent
        result = await self.agent.run_agent(ticker, job_id)
        
        if result.get("success"):
            excel_path = result.get("excel_path")
            reasoning = result.get("reasoning", "")
            
            # Build result data for storage
            result_data = {
                "company_metadata": {"ticker": ticker},
                "reasoning": reasoning,
                "tool_calls": result.get("tool_calls", []),
                "iterations": result.get("iterations", 0),
                "elapsed_seconds": result.get("elapsed_seconds", 0)
            }
            
            # Try to extract valuation and thesis from the final result
            # The agent stores these in the Excel model data
            
            # Mark job as completed
            await self.db.model_jobs.update_one(
                {"job_id": job_id},
                {"$set": {
                    "status": "completed",
                    "current_step": 8,
                    "excel_path": excel_path,
                    "result": result_data,
                    "reasoning": reasoning,
                    "completed_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            await ws_manager.send_job_update(job_id, {
                "status": "completed",
                "excel_path": excel_path,
                "current_step": 8,
                "reasoning": reasoning
            })
            
            await ws_manager.send_activity(
                job_id, "success",
                f"✅ Financial model completed for {ticker}",
                {"excel_path": excel_path}
            )
        else:
            error_msg = result.get("error", "Unknown error")
            await self._handle_pipeline_error(job_id, error_msg)
    
    async def _run_sequential_pipeline(self, job_id: str, ticker: str):
        """Run the legacy sequential 8-step pipeline"""
        logger.info(f"Running SEQUENTIAL pipeline for {ticker}")
        
        # Set job_id for activity logging in ClaudeService
        self.claude.set_job_id(job_id)
        
        # Broadcast pipeline start
        await ws_manager.send_activity(job_id, "info", f"Starting analysis pipeline for {ticker}")
        
        # Initialize job steps
        await self._init_job_steps(job_id)
        
        # Step 1: Company Identification
        company_metadata = await self._step1_company_identification(job_id, ticker)
        
        # Step 2: Annual Financial Data
        historical_financials = await self._step2_annual_financial_data(job_id, ticker, company_metadata)
        
        # Step 3: Operational Metrics
        operational_data = await self._step3_operational_metrics(job_id, ticker, company_metadata)
        
        # Step 4: Management Commentary
        management_commentary = await self._step4_management_commentary(job_id, ticker, company_metadata)
        
        # Step 5: Assumptions Generation
        assumptions = await self._step5_assumptions_generation(
            job_id, ticker, company_metadata, historical_financials,
            operational_data, management_commentary
        )
        
        # Step 6: Valuation (moved before Excel)
        valuation = await self._step6_valuation(job_id, company_metadata, assumptions)
        
        # Step 7: Thesis Generation (moved before Excel) - now includes presentations data
        thesis = await self._step7_thesis_generation(
            job_id, company_metadata, historical_financials,
            assumptions, valuation, management_commentary
        )
        
        # Step 8: Excel Model Generation (now last, with all data)
        excel_path = await self._step8_excel_generation(
            job_id, ticker, company_metadata, historical_financials,
            operational_data, management_commentary, assumptions, valuation, thesis
        )
        
        # Mark job as completed
        await self._complete_job(job_id, excel_path, {
            'company_metadata': company_metadata,
            'valuation': valuation,
            'thesis': thesis,
            'assumptions': assumptions
        })
        
        logger.info(f"Pipeline completed successfully for job {job_id}")
    
    async def _handle_pipeline_error(self, job_id: str, error_message: str):
        """Handle pipeline error"""
        await self.db.model_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "failed",
                "error_message": error_message,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        await ws_manager.send_job_update(job_id, {
            "status": "failed",
            "error_message": error_message
        })
        
        await ws_manager.send_activity(job_id, "error", f"Pipeline failed: {error_message[:200]}")
    
    async def _init_job_steps(self, job_id: str):
        """Initialize the 8 pipeline steps"""
        steps = [
            {"step_number": 1, "name": "Company Identification", "status": "pending", "message": ""},
            {"step_number": 2, "name": "Fetching Annual Financial Data", "status": "pending", "message": ""},
            {"step_number": 3, "name": "Extracting Operational Metrics", "status": "pending", "message": ""},
            {"step_number": 4, "name": "Processing Management Commentary", "status": "pending", "message": ""},
            {"step_number": 5, "name": "Generating Forecast Assumptions", "status": "pending", "message": ""},
            {"step_number": 6, "name": "Running Valuation", "status": "pending", "message": ""},
            {"step_number": 7, "name": "Writing Investment Thesis", "status": "pending", "message": ""},
            {"step_number": 8, "name": "Building Excel Model", "status": "pending", "message": ""},
        ]
        
        await self.db.model_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "steps": steps,
                "status": "processing",
                "current_step": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "estimated_completion": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
            }}
        )
    
    async def _update_step(self, job_id: str, step_number: int, status: str, message: str = "", data: Dict = None):
        """Update a specific step's status and broadcast via WebSocket"""
        step_update = {
            f"steps.{step_number - 1}.status": status,
            f"steps.{step_number - 1}.message": message,
            "current_step": step_number,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if status == "in_progress":
            step_update[f"steps.{step_number - 1}.started_at"] = datetime.now(timezone.utc).isoformat()
        elif status in ["completed", "error", "warning"]:
            step_update[f"steps.{step_number - 1}.completed_at"] = datetime.now(timezone.utc).isoformat()
        
        if data:
            step_update[f"steps.{step_number - 1}.data"] = data
        
        await self.db.model_jobs.update_one(
            {"id": job_id},
            {"$set": step_update}
        )
        
        # Broadcast via WebSocket
        await ws_manager.send_step_update(
            job_id=job_id,
            step_number=step_number,
            status=status,
            message=message,
            data=data
        )
    
    async def _step1_company_identification(self, job_id: str, ticker: str) -> Dict[str, Any]:
        """Step 1: Identify company and determine sector"""
        await self._update_step(job_id, 1, "in_progress", f"Identifying {ticker}...")
        await ws_manager.send_activity(job_id, "data_processing", f"Looking up {ticker} in financial databases...")
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 1)
            if cached_data:
                logger.info(f"Using cached step 1 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached company data, skipping API call")
                await self._update_step(
                    job_id, 1, "completed",
                    f"Identified: {cached_data.get('full_name')} - {cached_data.get('sector')} (from cache)",
                    cached_data
                )
                return cached_data
            
            # Scrape Screener.in
            await ws_manager.send_activity(job_id, "data_processing", "Scraping Screener.in for company data...")
            screener_data = await self.scraper.scrape_screener(ticker)
            
            if not screener_data.get('scraped_successfully'):
                raise Exception(f"Could not find ticker {ticker} on Screener.in")
            
            await ws_manager.send_activity(job_id, "info", f"Found company: {screener_data.get('company_name', ticker)}")
            
            # Use Claude to extract metadata
            await ws_manager.send_activity(job_id, "llm_thinking", "Analyzing company data with Claude AI...")
            knowledge_file = self.claude.load_knowledge_file("banks.md")
            
            system_message = f"{knowledge_file}\n\nYou are a financial research assistant analyzing Indian companies."
            
            user_prompt = f"""
Given the ticker {ticker}, analyze the Screener.in data and identify:
- Full company name
- BSE code (if available)
- NSE code
- Sector and industry
- Which sector knowledge file applies (BANKS, GENERIC, etc.)
- Current market price
- Market capitalization (₹ Cr)
- Shares outstanding (Cr)
- Fiscal year end month
- Face value per share

Company name found: {screener_data.get('company_name')}

Return ONLY a JSON object with these exact keys:
{{
    "ticker": "{ticker}",
    "full_name": "Company Name",
    "bse_code": "BSE code or empty string",
    "nse_code": "NSE code",
    "sector": "Sector name",
    "industry": "Industry name",
    "knowledge_file": "banks.md or generic.md",
    "current_price": 0.0,
    "market_cap": 0.0,
    "shares_outstanding": 0.0,
    "fiscal_year_end": "March",
    "face_value": 0.0
}}
"""
            
            response = await self.claude.call_claude(system_message, user_prompt, f"job_{job_id}_step1")
            
            # Parse JSON response
            try:
                metadata = json.loads(response)
            except:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    metadata = json.loads(json_match.group())
                else:
                    metadata = {
                        "ticker": ticker,
                        "full_name": screener_data.get('company_name', ticker),
                        "bse_code": "",
                        "nse_code": ticker,
                        "sector": "Unknown",
                        "industry": "Unknown",
                        "knowledge_file": "generic.md",
                        "current_price": 0.0,
                        "market_cap": 0.0,
                        "shares_outstanding": 0.0,
                        "fiscal_year_end": "March",
                        "face_value": 10.0
                    }
            
            # Fetch current market price (always get fresh price)
            await ws_manager.send_activity(job_id, "api_call", "Fetching current market price...")
            price_data = await self.scraper.get_current_market_price(ticker)
            
            if price_data.get('current_price'):
                metadata['current_price'] = price_data['current_price']
                metadata['price_fetched_at'] = price_data.get('price_fetched_at')
                if price_data.get('market_cap'):
                    metadata['market_cap'] = price_data['market_cap']
                if price_data.get('book_value'):
                    metadata['book_value'] = price_data['book_value']
                if price_data.get('pe_ratio'):
                    metadata['pe_ratio'] = price_data['pe_ratio']
                await ws_manager.send_activity(job_id, "info", f"Current price: ₹{price_data['current_price']:,.2f}")
            
            # Cache the result
            CacheService.save_step_data(ticker, 1, metadata)
            
            await self._update_step(
                job_id, 1, "completed",
                f"Identified: {metadata.get('full_name')} - {metadata.get('sector')}",
                metadata
            )
            
            return metadata
            
        except Exception as e:
            await self._update_step(job_id, 1, "error", str(e))
            raise
    
    async def _step2_annual_financial_data(self, job_id: str, ticker: str, company_metadata: Dict) -> Dict[str, Any]:
        """Step 2: Scrape annual P&L and Balance Sheet from Screener.in"""
        await self._update_step(job_id, 2, "in_progress", "Scraping annual financials from Screener.in...")
        await ws_manager.send_activity(job_id, "data_processing", "Extracting P&L and Balance Sheet tables...")
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 2)
            if cached_data and cached_data.get('annual_pnl') and cached_data.get('scraped_successfully'):
                logger.info(f"Using cached step 2 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached financial data")
                years = cached_data.get('years', [])
                await self._update_step(job_id, 2, "completed", f"Financial data extracted ({len(years)} years) (from cache)")
                return cached_data
            
            await ws_manager.send_activity(job_id, "api_call", f"Scraping Screener.in/company/{ticker}...")
            
            # Actually scrape from Screener.in
            financial_data = await self.scraper.scrape_annual_financials(ticker)
            
            if not financial_data.get('scraped_successfully'):
                await ws_manager.send_activity(job_id, "error", "Scraping failed, check logs")
                logger.warning(f"Scraping failed for {ticker}, error: {financial_data.get('error')}")
            else:
                years = financial_data.get('years', [])
                pnl_items = len(financial_data.get('annual_pnl', {}).get(years[0], {})) if years else 0
                await ws_manager.send_activity(job_id, "info", f"Scraped {len(years)} years, {pnl_items} P&L line items")
            
            # Cache the result
            CacheService.save_step_data(ticker, 2, financial_data)
            
            years_count = len(financial_data.get('years', []))
            await self._update_step(job_id, 2, "completed", f"Scraped {years_count} years of financial data")
            return financial_data
            
        except Exception as e:
            await self._update_step(job_id, 2, "error", str(e))
            raise
    
    async def _step3_operational_metrics(self, job_id: str, ticker: str, company_metadata: Dict) -> Dict[str, Any]:
        """Step 3: Scrape quarterly results from Screener.in"""
        await self._update_step(job_id, 3, "in_progress", "Scraping quarterly results from Screener.in...")
        await ws_manager.send_activity(job_id, "data_processing", "Extracting quarterly P&L data...")
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 3)
            if cached_data and cached_data.get('quarterly_results') and cached_data.get('scraped_successfully'):
                logger.info(f"Using cached step 3 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached quarterly data")
                quarters = cached_data.get('quarters', [])
                await self._update_step(job_id, 3, "completed", f"Quarterly data extracted ({len(quarters)} quarters) (from cache)")
                return cached_data
            
            await ws_manager.send_activity(job_id, "api_call", f"Scraping quarterly data from Screener.in...")
            
            # Actually scrape quarterly results
            quarterly_data = await self.scraper.scrape_quarterly_results(ticker)
            
            if not quarterly_data.get('scraped_successfully'):
                await ws_manager.send_activity(job_id, "error", "Quarterly scraping failed")
                logger.warning(f"Quarterly scraping failed for {ticker}")
            else:
                quarters = quarterly_data.get('quarters', [])
                await ws_manager.send_activity(job_id, "info", f"Scraped {len(quarters)} quarters of data")
            
            # Cache the result
            CacheService.save_step_data(ticker, 3, quarterly_data)
            
            quarters_count = len(quarterly_data.get('quarters', []))
            await self._update_step(job_id, 3, "completed", f"Scraped {quarters_count} quarters of data")
            return quarterly_data
            
        except Exception as e:
            await self._update_step(job_id, 3, "error", str(e))
            raise
    
    async def _step4_management_commentary(self, job_id: str, ticker: str, company_metadata: Dict) -> Dict[str, Any]:
        """Step 4: Scrape management commentary + presentations + extract metrics from PDFs"""
        await self._update_step(job_id, 4, "in_progress", "Scraping management commentary and investor presentations...")
        await ws_manager.send_activity(job_id, "data_processing", "Extracting pros, cons, peers, investor presentations...")
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 4)
            if cached_data and cached_data.get('scraped_successfully') and cached_data.get('pdf_metrics_extracted'):
                logger.info(f"Using cached step 4 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached commentary with PDF metrics")
                await self._update_step(job_id, 4, "completed", "Commentary extracted (from cache)")
                return cached_data
            
            await ws_manager.send_activity(job_id, "api_call", "Scraping analysis from Screener.in...")
            
            # Scrape commentary (pros/cons)
            commentary_data = await self.scraper.scrape_concall_commentary(ticker)
            
            # Also get enhanced data (peers, shareholding)
            await ws_manager.send_activity(job_id, "api_call", "Scraping peer comparison and shareholding...")
            enhanced_data = await self.scraper._scrape_enhanced_screener_data(ticker)
            
            # Scrape investor presentations from Screener Documents
            await ws_manager.send_activity(job_id, "api_call", "Scraping investor presentations from Screener...")
            bse_code = company_metadata.get('bse_code', '')
            company_name = company_metadata.get('full_name', '')
            pres_data = await self.scraper.scrape_bse_investor_presentation(ticker, bse_code, company_name)
            
            # Merge all data
            commentary_data['peer_comparison'] = enhanced_data.get('peer_comparison', [])
            commentary_data['shareholding'] = enhanced_data.get('shareholding', {})
            commentary_data['operational_metrics'] = enhanced_data.get('operational_metrics', {})
            
            # Add presentation data
            commentary_data['bse_presentations'] = pres_data.get('presentations', [])
            commentary_data['presentation_summaries'] = pres_data.get('presentation_summaries', [])
            commentary_data['transcripts'] = pres_data.get('transcripts', [])
            commentary_data['annual_reports'] = pres_data.get('annual_reports', [])
            
            # ===== NEW: Extract metrics from PDF presentations =====
            presentations = commentary_data.get('bse_presentations', [])
            if presentations:
                await ws_manager.send_activity(job_id, "data_processing", f"Downloading and parsing {min(len(presentations), 2)} investor presentation PDFs...")
                
                # Determine if it's a bank
                sector = company_metadata.get('sector', '').lower()
                is_bank = 'bank' in sector or 'financ' in sector or 'nbfc' in sector
                
                # Process PDFs and extract metrics from investor presentations
                pdf_metrics = await self.pdf_extractor.process_presentations(
                    presentations, 
                    self.claude, 
                    is_bank=is_bank,
                    max_pdfs=2  # Limit to 2 PDFs to save time
                )
                
                commentary_data['pdf_extracted_metrics'] = pdf_metrics
                commentary_data['pdf_metrics_extracted'] = pdf_metrics.get('extracted_from_pdfs', 0) > 0
                
                # Merge extracted metrics into operational_metrics
                if pdf_metrics.get('latest_metrics'):
                    commentary_data['operational_metrics'].update(pdf_metrics['latest_metrics'])
                
                # Add guidance and highlights
                commentary_data['management_guidance'] = pdf_metrics.get('guidance', [])
                commentary_data['key_highlights'] = pdf_metrics.get('key_highlights', [])
                
                await ws_manager.send_activity(
                    job_id, "info", 
                    f"Extracted metrics from {pdf_metrics.get('extracted_from_pdfs', 0)} PDFs: "
                    f"{len(pdf_metrics.get('latest_metrics', {}))} metrics found"
                )
            else:
                commentary_data['pdf_metrics_extracted'] = False
                commentary_data['pdf_extracted_metrics'] = {}
            
            # ===== NEW: Process Annual Reports for detailed financials =====
            annual_reports = commentary_data.get('annual_reports', [])
            if annual_reports:
                await ws_manager.send_activity(job_id, "data_processing", f"Parsing {min(len(annual_reports), 1)} annual report for detailed financials...")
                
                sector = company_metadata.get('sector', '').lower()
                is_bank = 'bank' in sector or 'financ' in sector or 'nbfc' in sector
                
                annual_report_data = await self.pdf_extractor.process_annual_reports(
                    annual_reports,
                    self.claude,
                    is_bank=is_bank,
                    max_reports=1  # Latest year only for speed
                )
                
                commentary_data['annual_report_financials'] = annual_report_data
                
                # Store detailed P&L and BS for Excel generation
                if annual_report_data.get('detailed_pnl'):
                    commentary_data['detailed_pnl'] = annual_report_data['detailed_pnl']
                if annual_report_data.get('detailed_bs'):
                    commentary_data['detailed_bs'] = annual_report_data['detailed_bs']
                
                reports_processed = annual_report_data.get('reports_processed', 0)
                await ws_manager.send_activity(
                    job_id, "info",
                    f"Extracted detailed financials from {reports_processed} annual reports"
                )
            
            # ===== NEW: Process Concall Transcripts (last 4 quarters) =====
            transcripts = commentary_data.get('transcripts', [])
            if transcripts:
                await ws_manager.send_activity(job_id, "data_processing", f"Parsing {min(len(transcripts), 2)} concall transcripts...")
                
                transcript_data = await self.pdf_extractor.process_concall_transcripts(
                    transcripts,
                    self.claude,
                    max_transcripts=2  # Reduced from 4 to 2 for speed
                )
                
                commentary_data['transcript_insights'] = transcript_data
                
                # Add transcript insights to management guidance
                if transcript_data.get('guidance_statements'):
                    existing_guidance = commentary_data.get('management_guidance', [])
                    for g in transcript_data['guidance_statements']:
                        if g not in existing_guidance:
                            existing_guidance.append(g)
                    commentary_data['management_guidance'] = existing_guidance
                
                # Add key themes
                commentary_data['concall_themes'] = transcript_data.get('key_themes', [])
                commentary_data['analyst_concerns'] = transcript_data.get('analyst_concerns', [])
                commentary_data['management_outlook'] = transcript_data.get('management_outlook', [])
                
                transcripts_processed = transcript_data.get('transcripts_processed', 0)
                await ws_manager.send_activity(
                    job_id, "info",
                    f"Parsed {transcripts_processed} concall transcripts, extracted {len(transcript_data.get('key_themes', []))} themes"
                )
            
            if not commentary_data.get('scraped_successfully') and not enhanced_data.get('scraped_successfully'):
                await ws_manager.send_activity(job_id, "error", "Commentary scraping failed")
                logger.warning(f"Commentary scraping failed for {ticker}")
            else:
                commentary_data['scraped_successfully'] = True
                pros_count = len(commentary_data.get('pros', []))
                cons_count = len(commentary_data.get('cons', []))
                peers_count = len(commentary_data.get('peer_comparison', []))
                pres_count = len(commentary_data.get('bse_presentations', []))
                pdf_count = commentary_data.get('pdf_extracted_metrics', {}).get('extracted_from_pdfs', 0)
                ar_count = commentary_data.get('annual_report_financials', {}).get('reports_processed', 0)
                await ws_manager.send_activity(
                    job_id, "info", 
                    f"Scraped {pros_count} pros, {cons_count} cons, {pres_count} PPTs parsed, {ar_count} annual reports parsed"
                )
            
            # Cache the result
            CacheService.save_step_data(ticker, 4, commentary_data)
            
            pros = len(commentary_data.get('pros', []))
            cons = len(commentary_data.get('cons', []))
            peers = len(commentary_data.get('peer_comparison', []))
            pres = len(commentary_data.get('bse_presentations', []))
            pdfs = commentary_data.get('pdf_extracted_metrics', {}).get('extracted_from_pdfs', 0)
            ar_count = commentary_data.get('annual_report_financials', {}).get('reports_processed', 0)
            await self._update_step(job_id, 4, "completed", f"{pros} pros, {cons} cons, {pdfs} PPTs, {ar_count} annual reports")
            return commentary_data
            
        except Exception as e:
            await self._update_step(job_id, 4, "error", str(e))
            raise
    
    async def _step5_assumptions_generation(self, job_id: str, ticker: str, company_metadata: Dict,
                                           historical_financials: Dict, operational_data: Dict,
                                           management_commentary: Dict) -> Dict[str, Any]:
        """Step 5: Generate forecast assumptions using Claude"""
        await self._update_step(job_id, 5, "in_progress", "Generating forecast assumptions...")
        await ws_manager.send_activity(job_id, "llm_thinking", "Claude AI building 5-year forecast model assumptions...")
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 5)
            if cached_data:
                logger.info(f"Using cached step 5 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached forecast assumptions")
                await self._update_step(job_id, 5, "completed", "Forecast assumptions generated (from cache)")
                return cached_data
            
            await ws_manager.send_activity(job_id, "data_processing", "Preparing data context for assumption generation...")
            
            # Get sector type from metadata
            sector = company_metadata.get('sector', 'Unknown').lower()
            is_bank = 'bank' in sector or 'financial' in sector
            
            # Build a FOCUSED system message (not the entire knowledge file)
            if is_bank:
                system_message = """You are a senior equity research analyst specializing in Indian banks.
You generate realistic 5-year forecast assumptions based on historical data and industry norms.

Key metrics to forecast for banks:
- Loan Growth Rate (typically 1-1.5x GDP growth for large banks)
- NIM (Net Interest Margin) - typically 3-4.5% for private banks
- CASA Ratio - higher is better, 40-50% typical
- Cost of Deposits - linked to repo rate
- Credit Cost - 0.5-2% depending on asset quality
- Cost-to-Income Ratio - 40-50% for efficient banks
- ROA - 1-2% for well-run banks
- ROE - 12-18% typical
- Capital Adequacy - minimum 11.5% per RBI

Always return valid JSON."""
            else:
                system_message = """You are a senior equity research analyst.
You generate realistic 5-year forecast assumptions based on historical data and industry norms.

Key metrics to forecast:
- Revenue Growth Rate
- EBITDA Margin
- Depreciation as % of Gross Block
- Tax Rate
- Working Capital Days
- Capex as % of Revenue
- ROE and ROCE

Always return valid JSON."""

            # Build context from available data
            await ws_manager.send_activity(job_id, "data_processing", "Analyzing historical trends...")
            
            data_context = f"""
Company: {company_metadata.get('full_name', ticker)}
Ticker: {ticker}
Sector: {company_metadata.get('sector', 'Unknown')}
Industry: {company_metadata.get('industry', 'Unknown')}
Current Price: ₹{company_metadata.get('current_price', 'N/A')}
Market Cap: ₹{company_metadata.get('market_cap', 'N/A')} Cr
"""

            # Add historical financials summary if available
            if historical_financials and historical_financials.get('annual_pnl'):
                data_context += "\nHistorical Financial Data Available: Yes"
            else:
                data_context += "\nHistorical Financial Data Available: Limited"

            # ===== NEW: Add PDF-extracted metrics for more accurate assumptions =====
            pdf_metrics = management_commentary.get('pdf_extracted_metrics', {}) if management_commentary else {}
            latest_metrics = pdf_metrics.get('latest_metrics', {})
            
            if latest_metrics:
                data_context += "\n\nLATEST METRICS FROM INVESTOR PRESENTATION:"
                for key, value in latest_metrics.items():
                    if key not in ['guidance', 'key_highlights']:
                        data_context += f"\n- {key.replace('_', ' ').title()}: {value}"
            
            # Add management guidance from PDFs
            guidance = management_commentary.get('management_guidance', []) if management_commentary else []
            if guidance:
                data_context += "\n\nMANAGEMENT GUIDANCE (from investor presentations):"
                for g in guidance[:5]:
                    data_context += f"\n- {g}"
            
            # Add key highlights from PDFs
            highlights = management_commentary.get('key_highlights', []) if management_commentary else []
            if highlights:
                data_context += "\n\nKEY OPERATIONAL HIGHLIGHTS:"
                for h in highlights[:5]:
                    data_context += f"\n- {h}"
            
            # Add operational metrics from Screener
            op_metrics = management_commentary.get('operational_metrics', {}) if management_commentary else {}
            if op_metrics:
                data_context += "\n\nOPERATIONAL METRICS:"
                for key, value in list(op_metrics.items())[:10]:
                    data_context += f"\n- {key}: {value}"
            
            await ws_manager.send_activity(job_id, "api_call", "Calling Claude API for assumptions generation...")
            
            # Build example JSON based on sector type
            if is_bank:
                example_json = '''{
    "forecast_years": ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"],
    "assumptions": {
        "loan_growth_rate": [0.15, 0.14, 0.13, 0.12, 0.11],
        "nim": [0.038, 0.037, 0.036, 0.035, 0.035],
        "casa_ratio": [0.45, 0.46, 0.47, 0.48, 0.48],
        "credit_cost": [0.012, 0.011, 0.010, 0.010, 0.009],
        "cost_to_income": [0.45, 0.44, 0.43, 0.42, 0.41],
        "roa": [0.015, 0.016, 0.017, 0.017, 0.018],
        "roe": [0.15, 0.155, 0.16, 0.165, 0.17]
    },
    "rationale": "Brief explanation of key assumptions"
}'''
            else:
                example_json = '''{
    "forecast_years": ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"],
    "assumptions": {
        "revenue_growth_rate": [0.12, 0.11, 0.10, 0.09, 0.08],
        "ebitda_margin": [0.18, 0.19, 0.20, 0.20, 0.21],
        "tax_rate": [0.25, 0.25, 0.25, 0.25, 0.25],
        "capex_pct_revenue": [0.05, 0.05, 0.04, 0.04, 0.04],
        "working_capital_days": [45, 44, 43, 42, 41],
        "depreciation_rate": [0.10, 0.10, 0.10, 0.10, 0.10],
        "roe": [0.15, 0.155, 0.16, 0.165, 0.17]
    },
    "rationale": "Brief explanation of key assumptions"
}'''
            
            user_prompt = f"""{data_context}

Generate forecast assumptions for FY26E through FY30E (5 years).

Return a JSON object with this structure:
{example_json}

Adjust the numbers based on the company's historical performance and sector outlook.
Return ONLY the JSON object, no other text."""
            
            response = await self.claude.call_claude(system_message, user_prompt, f"job_{job_id}_step5")
            
            await ws_manager.send_activity(job_id, "data_processing", "Parsing assumptions response...")
            
            try:
                assumptions = json.loads(response)
            except:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    try:
                        assumptions = json.loads(json_match.group())
                    except:
                        assumptions = self._get_default_assumptions(is_bank)
                else:
                    assumptions = self._get_default_assumptions(is_bank)
            
            # Cache the result
            CacheService.save_step_data(ticker, 5, assumptions)
            
            await self._update_step(job_id, 5, "completed", "Forecast assumptions generated")
            return assumptions
            
        except Exception as e:
            await self._update_step(job_id, 5, "error", str(e))
            raise
    
    def _get_default_assumptions(self, is_bank: bool) -> Dict[str, Any]:
        """Return default assumptions if parsing fails"""
        if is_bank:
            return {
                "forecast_years": ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"],
                "assumptions": {
                    "loan_growth_rate": [0.15, 0.14, 0.13, 0.12, 0.11],
                    "nim": [0.038, 0.037, 0.036, 0.035, 0.035],
                    "casa_ratio": [0.45, 0.46, 0.47, 0.48, 0.48],
                    "credit_cost": [0.012, 0.011, 0.010, 0.010, 0.009],
                    "cost_to_income": [0.45, 0.44, 0.43, 0.42, 0.41],
                    "roa": [0.015, 0.016, 0.017, 0.017, 0.018],
                    "roe": [0.15, 0.155, 0.16, 0.165, 0.17]
                },
                "rationale": "Default assumptions for Indian private sector bank"
            }
        else:
            return {
                "forecast_years": ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"],
                "assumptions": {
                    "revenue_growth_rate": [0.12, 0.11, 0.10, 0.09, 0.08],
                    "ebitda_margin": [0.18, 0.19, 0.20, 0.20, 0.21],
                    "tax_rate": [0.25, 0.25, 0.25, 0.25, 0.25],
                    "capex_pct_revenue": [0.05, 0.05, 0.04, 0.04, 0.04],
                    "working_capital_days": [45, 44, 43, 42, 41],
                    "depreciation_rate": [0.10, 0.10, 0.10, 0.10, 0.10],
                    "roe": [0.15, 0.155, 0.16, 0.165, 0.17]
                },
                "rationale": "Default assumptions for Indian company"
            }
    
    async def _step6_valuation(self, job_id: str, company_metadata: Dict, assumptions: Dict) -> Dict[str, Any]:
        """Step 6: Run valuation"""
        await self._update_step(job_id, 6, "in_progress", "Running valuation...")
        await ws_manager.send_activity(job_id, "llm_thinking", "Claude AI calculating intrinsic value...")
        
        ticker = company_metadata.get('ticker', 'UNKNOWN')
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 6)
            if cached_data:
                logger.info(f"Using cached step 6 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached valuation data")
                await self._update_step(job_id, 6, "completed", "Valuation complete (from cache)")
                return cached_data
            
            await ws_manager.send_activity(job_id, "data_processing", "Calculating cost of equity and target price...")
            
            # Get sector type
            sector = company_metadata.get('sector', 'Unknown').lower()
            is_bank = 'bank' in sector or 'financial' in sector
            current_price = company_metadata.get('current_price', 100)
            
            # Focused system message (NOT the full knowledge file)
            system_message = """You are a quantitative equity analyst specializing in Indian markets.
You perform stock valuations using the Residual Income Valuation (RIV) method.

Key inputs:
- Risk-free rate (Rf): 7% (10-year G-Sec yield)
- Equity Risk Premium (ERP): 6%
- Beta: Use 1.0 for large-cap banks, 1.2 for mid-cap

Output a concise JSON with valuation results. Always return valid JSON."""

            # Concise user prompt with actual data
            roe_assumption = assumptions.get('assumptions', {}).get('roe', [0.15])[0] if isinstance(assumptions.get('assumptions', {}).get('roe'), list) else 0.15
            
            user_prompt = f"""Perform RIV valuation for {company_metadata.get('full_name')}:

Company Data:
- Current Price: ₹{current_price}
- Market Cap: ₹{company_metadata.get('market_cap', 0)} Cr
- Sector: {company_metadata.get('sector', 'Unknown')}
- ROE Assumption: {roe_assumption:.1%}

Calculate and return JSON:
{{
    "cost_of_equity": 13.0,
    "terminal_growth": 4.0,
    "fair_value": 0,
    "target_price": 0,
    "current_price": {current_price},
    "upside_percent": 0,
    "recommendation": "BUY/HOLD/SELL",
    "methodology": "RIV",
    "rationale": "Brief 1-2 sentence rationale"
}}

Adjust fair_value/target_price based on realistic assumptions for Indian {company_metadata.get('sector', 'financial')} sector.
Return ONLY the JSON."""
            
            await ws_manager.send_activity(job_id, "api_call", "Calling Claude API for valuation...")
            response = await self.claude.call_claude(system_message, user_prompt, f"job_{job_id}_step7")
            
            try:
                valuation = json.loads(response)
            except:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    try:
                        valuation = json.loads(json_match.group())
                    except:
                        valuation = self._get_default_valuation(current_price)
                else:
                    valuation = self._get_default_valuation(current_price)
            
            # Cache the result
            CacheService.save_step_data(ticker, 6, valuation)
            
            await self._update_step(job_id, 6, "completed", f"Valuation complete: {valuation.get('recommendation', 'N/A')}")
            return valuation
            
        except Exception as e:
            await self._update_step(job_id, 7, "error", str(e))
            raise
    
    def _get_default_valuation(self, current_price: float) -> Dict[str, Any]:
        """Return default valuation if parsing fails"""
        return {
            "cost_of_equity": 13.0,
            "terminal_growth": 4.0,
            "fair_value": current_price * 1.1,
            "target_price": current_price * 1.1,
            "current_price": current_price,
            "upside_percent": 10.0,
            "recommendation": "HOLD",
            "methodology": "RIV",
            "rationale": "Default valuation - insufficient data for precise estimate"
        }
    
    async def _step7_thesis_generation(self, job_id: str, company_metadata: Dict,
                                      historical_financials: Dict, assumptions: Dict,
                                      valuation: Dict, management_commentary: Dict = None) -> Dict[str, Any]:
        """Step 7: Generate investment thesis using all collected data including PDF-extracted metrics"""
        await self._update_step(job_id, 7, "in_progress", "Writing investment thesis...")
        await ws_manager.send_activity(job_id, "llm_thinking", "Claude AI writing investment note...")
        
        ticker = company_metadata.get('ticker', 'UNKNOWN')
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 7)
            if cached_data:
                logger.info(f"Using cached step 7 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached thesis")
                await self._update_step(job_id, 7, "completed", "Investment thesis generated (from cache)")
                return cached_data
            
            await ws_manager.send_activity(job_id, "data_processing", "Compiling key findings from financials, PDFs, and investor presentations...")
            
            # Focused system message
            system_message = """You are a senior equity research analyst at a top investment bank.
Write concise, professional investment notes in the style of institutional research.
Use specific metrics and data points from investor presentations.
Use bullet points for key metrics. Be direct and actionable."""

            # Build concise prompt with available data
            target_price = valuation.get('target_price', valuation.get('fair_value', 0))
            recommendation = valuation.get('recommendation', 'HOLD')
            upside = valuation.get('upside_percent', 0)
            
            # Extract key info from management commentary
            pros = management_commentary.get('pros', []) if management_commentary else []
            cons = management_commentary.get('cons', []) if management_commentary else []
            presentations = management_commentary.get('bse_presentations', []) if management_commentary else []
            
            # ===== NEW: Get PDF-extracted metrics =====
            pdf_metrics = management_commentary.get('pdf_extracted_metrics', {}) if management_commentary else {}
            latest_metrics = pdf_metrics.get('latest_metrics', {})
            guidance = management_commentary.get('management_guidance', []) if management_commentary else []
            highlights = management_commentary.get('key_highlights', []) if management_commentary else []
            
            # Build context from presentations
            presentation_context = ""
            if presentations:
                pres_quarters = [p.get('quarter', 'N/A') for p in presentations[:5] if p.get('quarter')]
                if pres_quarters:
                    presentation_context = f"\nQUARTERS WITH PRESENTATIONS: {', '.join(pres_quarters)}"
            
            # ===== NEW: Add actual metrics from PDF extraction =====
            metrics_context = ""
            if latest_metrics:
                metrics_context = "\n\nKEY METRICS FROM LATEST INVESTOR PRESENTATION:"
                metric_labels = {
                    'nim': 'Net Interest Margin',
                    'casa': 'CASA Ratio',
                    'gnpa': 'Gross NPA',
                    'nnpa': 'Net NPA',
                    'car': 'Capital Adequacy',
                    'roe': 'ROE',
                    'roa': 'ROA',
                    'cost_to_income': 'Cost-to-Income',
                    'loan_growth': 'Loan Growth',
                    'deposit_growth': 'Deposit Growth',
                    'provision_coverage': 'Provision Coverage',
                }
                for key, value in latest_metrics.items():
                    if key in metric_labels and isinstance(value, (int, float)):
                        metrics_context += f"\n- {metric_labels[key]}: {value:.2f}%"
            
            # Add management guidance from PDFs
            guidance_context = ""
            if guidance:
                guidance_context = "\n\nMANAGEMENT GUIDANCE (from investor presentations):"
                for g in guidance[:4]:
                    guidance_context += f"\n- {g}"
            
            # Add key highlights
            highlights_context = ""
            if highlights:
                highlights_context = "\n\nOPERATIONAL HIGHLIGHTS:"
                for h in highlights[:4]:
                    highlights_context += f"\n- {h}"
            
            # ===== NEW: Add concall transcript insights =====
            concall_context = ""
            concall_themes = management_commentary.get('concall_themes', []) if management_commentary else []
            mgmt_outlook = management_commentary.get('management_outlook', []) if management_commentary else []
            analyst_concerns = management_commentary.get('analyst_concerns', []) if management_commentary else []
            
            if concall_themes or mgmt_outlook:
                concall_context = "\n\nCONCALL INSIGHTS:"
                if mgmt_outlook:
                    concall_context += "\nManagement Outlook:"
                    for m in mgmt_outlook[:3]:
                        concall_context += f"\n- {m}"
                if concall_themes:
                    concall_context += "\nKey Themes:"
                    for t in concall_themes[:3]:
                        concall_context += f"\n- {t}"
                if analyst_concerns:
                    concall_context += "\nAnalyst Concerns:"
                    for c in analyst_concerns[:2]:
                        concall_context += f"\n- {c}"
            
            # Build strengths/risks context
            strengths_text = ""
            if pros:
                strengths_text = "\nSTRENGTHS (from Screener.in):\n" + "\n".join([f"- {p}" for p in pros[:4]])
            
            risks_text = ""
            if cons:
                risks_text = "\nRISKS (from Screener.in):\n" + "\n".join([f"- {c}" for c in cons[:4]])
            
            user_prompt = f"""Write a detailed investment thesis for {company_metadata.get('full_name')} ({ticker}).

KEY DATA:
- Current Price: ₹{company_metadata.get('current_price', 0):,.2f}
- Target Price: ₹{target_price:,.0f}
- Recommendation: {recommendation}
- Upside: {upside:.1f}%
- Sector: {company_metadata.get('sector', 'N/A')}
- Market Cap: ₹{company_metadata.get('market_cap', 0):,.0f} Cr
{presentation_context}
{metrics_context}
{guidance_context}
{highlights_context}
{concall_context}
{strengths_text}
{risks_text}

Write 4-6 short paragraphs covering:
1. RECOMMENDATION SUMMARY (1-2 sentences with price targets)
2. INVESTMENT CASE (3-4 bullet points on why to invest)
3. KEY RISKS (2-3 bullet points on what could go wrong)
4. VALUATION (brief note on methodology and fair value)

Keep total length under 500 words. Professional tone, no marketing language.
Reference the company's strengths and risks in your analysis."""
            
            await ws_manager.send_activity(job_id, "api_call", "Calling Claude API for thesis generation...")
            response = await self.claude.call_claude(system_message, user_prompt, f"job_{job_id}_step8")
            
            thesis = {
                "full_text": response,
                "summary": f"{recommendation} with target price of ₹{target_price}",
                "recommendation": recommendation,
                "target_price": target_price,
                "upside": upside,
                "presentations_referenced": len(presentations)
            }
            
            # Cache the result
            CacheService.save_step_data(ticker, 7, thesis)
            
            await self._update_step(job_id, 7, "completed", f"Thesis: {recommendation} - TP ₹{target_price}")
            return thesis
            
        except Exception as e:
            await self._update_step(job_id, 7, "error", str(e))
            raise
    
    async def _step8_excel_generation(self, job_id: str, ticker: str, company_metadata: Dict,
                                     historical_financials: Dict, operational_data: Dict,
                                     management_commentary: Dict, assumptions: Dict, 
                                     valuation: Dict, thesis: Dict) -> str:
        """Step 8: Generate Excel model with all collected data"""
        await self._update_step(job_id, 8, "in_progress", "Building Excel model...")
        await ws_manager.send_activity(job_id, "data_processing", "Creating multi-sheet financial model with formulas and ROE tree...")
        
        try:
            await ws_manager.send_activity(job_id, "info", "Compiling assumptions, valuation, thesis, and BSE data into Excel...")
            
            # Build complete data package for Excel
            data = {
                'company_metadata': company_metadata,
                'historical_financials': historical_financials,
                'operational_data': operational_data,
                'management_commentary': management_commentary,  # Includes BSE presentations
                'assumptions': assumptions,
                'valuation': valuation,
                'thesis': thesis
            }
            
            await ws_manager.send_activity(job_id, "data_processing", "Generating Excel file with mechanical linking and ROE tree...")
            excel_path = self.excel_gen.generate_model(job_id, data)
            
            await self._update_step(job_id, 8, "completed", f"Excel model generated: {excel_path}")
            return excel_path
            
        except Exception as e:
            await self._update_step(job_id, 8, "error", str(e))
            raise
    
    async def _complete_job(self, job_id: str, excel_path: str, result: Dict[str, Any]):
        """Mark job as completed and broadcast via WebSocket"""
        await self.db.model_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "excel_path": excel_path,
                "result": result,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Broadcast completion via WebSocket
        await ws_manager.send_completion(job_id, result)
    
    async def _fail_job(self, job_id: str, error: str):
        """Mark job as failed and broadcast via WebSocket"""
        await self.db.model_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "failed",
                "error": error,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Broadcast error via WebSocket
        await ws_manager.send_error(job_id, error)
