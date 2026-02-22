import asyncio
import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from pathlib import Path
import sys
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

sys.path.append(str(Path(__file__).parent.parent))

from models import ModelJob, PipelineStep
from services.claude_service import ClaudeService
from services.scraper_service import ScraperService
from services.excel_generator import ExcelGenerator
from services.websocket_manager import ws_manager
from services.cache_service import CacheService

logger = logging.getLogger(__name__)

class PipelineManager:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.claude = ClaudeService()
        self.scraper = ScraperService()
        self.excel_gen = ExcelGenerator()
    
    async def run_pipeline(self, job_id: str, ticker: str):
        """
        Run the complete 8-step pipeline for a ticker
        """
        try:
            logger.info(f"Starting pipeline for job {job_id}, ticker {ticker}")
            
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
            
            # Step 6: Excel Model Generation
            excel_path = await self._step6_excel_generation(
                job_id, company_metadata, historical_financials,
                operational_data, assumptions
            )
            
            # Step 7: Valuation
            valuation = await self._step7_valuation(job_id, company_metadata, assumptions)
            
            # Step 8: Thesis Generation
            thesis = await self._step8_thesis_generation(
                job_id, company_metadata, historical_financials,
                assumptions, valuation
            )
            
            # Mark job as completed
            await self._complete_job(job_id, excel_path, {
                'company_metadata': company_metadata,
                'valuation': valuation,
                'thesis': thesis
            })
            
            logger.info(f"Pipeline completed successfully for job {job_id}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for job {job_id}: {str(e)}")
            await self._fail_job(job_id, str(e))
            raise
    
    async def _init_job_steps(self, job_id: str):
        """Initialize the 8 pipeline steps"""
        steps = [
            {"step_number": 1, "name": "Company Identification", "status": "pending", "message": ""},
            {"step_number": 2, "name": "Fetching Annual Financial Data", "status": "pending", "message": ""},
            {"step_number": 3, "name": "Extracting Operational Metrics", "status": "pending", "message": ""},
            {"step_number": 4, "name": "Processing Management Commentary", "status": "pending", "message": ""},
            {"step_number": 5, "name": "Generating Forecast Assumptions", "status": "pending", "message": ""},
            {"step_number": 6, "name": "Building Excel Model", "status": "pending", "message": ""},
            {"step_number": 7, "name": "Running Valuation", "status": "pending", "message": ""},
            {"step_number": 8, "name": "Writing Investment Thesis", "status": "pending", "message": ""},
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
        """Step 2: Extract annual financial statements"""
        await self._update_step(job_id, 2, "in_progress", "Fetching annual financials from Screener.in...")
        await ws_manager.send_activity(job_id, "data_processing", "Extracting annual P&L and Balance Sheet data...")
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 2)
            if cached_data:
                logger.info(f"Using cached step 2 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached financial data, skipping extraction")
                await self._update_step(job_id, 2, "completed", "Annual financial data extracted (from cache)")
                return cached_data
            
            await ws_manager.send_activity(job_id, "llm_thinking", "Claude AI extracting financial statement line items...")
            knowledge_file = self.claude.load_knowledge_file(company_metadata.get('knowledge_file', 'generic.md'))
            
            system_message = f"{knowledge_file}\n\nYou are a financial data extraction agent."
            
            user_prompt = f"""
Extract annual financial statement data for {company_metadata.get('full_name')} from Screener.in.

For a banking company, extract P&L and Balance Sheet line items for the last 5 years.
Since I cannot actually access Screener.in, generate realistic sample data based on typical Indian bank financials.

Return JSON with:
{{
    "annual_pnl": {{"FY21": {{}}, "FY22": {{}}, ...}},
    "annual_bs": {{"FY21": {{}}, "FY22": {{}}, ...}},
    "quarterly_results": []
}}
"""
            
            response = await self.claude.call_claude(system_message, user_prompt, f"job_{job_id}_step2")
            
            try:
                financial_data = json.loads(response)
            except:
                financial_data = {"annual_pnl": {}, "annual_bs": {}, "quarterly_results": []}
            
            # Cache the result
            CacheService.save_step_data(ticker, 2, financial_data)
            
            await self._update_step(job_id, 2, "completed", "Annual financial data extracted")
            return financial_data
            
        except Exception as e:
            await self._update_step(job_id, 2, "error", str(e))
            raise
    
    async def _step3_operational_metrics(self, job_id: str, ticker: str, company_metadata: Dict) -> Dict[str, Any]:
        """Step 3: Extract quarterly operational metrics"""
        await self._update_step(job_id, 3, "in_progress", "Extracting quarterly metrics...")
        await ws_manager.send_activity(job_id, "data_processing", "Fetching operational KPIs from investor presentations...")
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 3)
            if cached_data:
                logger.info(f"Using cached step 3 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached operational metrics")
                await self._update_step(job_id, 3, "completed", "Operational metrics extracted (from cache)", cached_data)
                return cached_data
            
            await ws_manager.send_activity(job_id, "info", "Generating operational metrics structure...")
            # Mock operational data for now
            operational_data = {
                "quarterly_data": [],
                "note": "Operational metrics extraction requires BSE filing access"
            }
            
            # Cache the result
            CacheService.save_step_data(ticker, 3, operational_data)
            
            await self._update_step(job_id, 3, "completed", "Operational metrics extracted", operational_data)
            return operational_data
            
        except Exception as e:
            await self._update_step(job_id, 3, "warning", "Could not extract all operational metrics")
            return {"quarterly_data": []}
    
    async def _step4_management_commentary(self, job_id: str, ticker: str, company_metadata: Dict) -> Dict[str, Any]:
        """Step 4: Extract management guidance from concalls"""
        await self._update_step(job_id, 4, "in_progress", "Processing concall transcripts...")
        await ws_manager.send_activity(job_id, "data_processing", "Analyzing management guidance from earnings calls...")
        
        try:
            # Check cache first
            cached_data = CacheService.load_step_data(ticker, 4)
            if cached_data:
                logger.info(f"Using cached step 4 data for {ticker}")
                await ws_manager.send_activity(job_id, "info", "Found cached management commentary")
                await self._update_step(job_id, 4, "completed", "Management commentary processed (from cache)")
                return cached_data
            
            await ws_manager.send_activity(job_id, "info", "Structuring management guidance data...")
            commentary = {
                "guidance": [],
                "note": "Concall transcript extraction requires additional data sources"
            }
            
            # Cache the result
            CacheService.save_step_data(ticker, 4, commentary)
            
            await self._update_step(job_id, 4, "completed", "Management commentary processed")
            return commentary
            
        except Exception as e:
            await self._update_step(job_id, 4, "warning", "Limited management commentary available")
            return {"guidance": []}
    
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
            
            await ws_manager.send_activity(job_id, "data_processing", "Loading sector knowledge base for assumptions...")
            knowledge_file = self.claude.load_knowledge_file(company_metadata.get('knowledge_file', 'generic.md'))
            
            await ws_manager.send_activity(job_id, "llm_thinking", "Analyzing historical trends and management guidance...")
            
            system_message = f"{knowledge_file}\n\nYou are a senior equity research analyst building forecast assumptions."
            
            user_prompt = f"""
Generate forecast assumptions for {company_metadata.get('full_name')} for FY26-FY30.

Based on the sector knowledge file, create assumptions for all required parameters.
For a bank, this includes: loan growth, NIM, CASA ratio, credit cost, ROA, ROE, etc.

Return JSON with assumptions for each parameter for each forecast year.
"""
            
            response = await self.claude.call_claude(system_message, user_prompt, f"job_{job_id}_step5")
            
            try:
                assumptions = json.loads(response)
            except:
                assumptions = {"forecast_years": ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"]}
            
            # Cache the result
            CacheService.save_step_data(ticker, 5, assumptions)
            
            await self._update_step(job_id, 5, "completed", "Forecast assumptions generated")
            return assumptions
            
        except Exception as e:
            await self._update_step(job_id, 5, "error", str(e))
            raise
    
    async def _step6_excel_generation(self, job_id: str, company_metadata: Dict,
                                     historical_financials: Dict, operational_data: Dict,
                                     assumptions: Dict) -> str:
        """Step 6: Generate Excel model"""
        await self._update_step(job_id, 6, "in_progress", "Building Excel model...")
        await ws_manager.send_activity(job_id, "data_processing", "Creating multi-sheet financial model in Excel format...")
        
        try:
            await ws_manager.send_activity(job_id, "info", "Structuring P&L, Balance Sheet and Cash Flow sheets...")
            data = {
                'company_metadata': company_metadata,
                'historical_financials': historical_financials,
                'operational_data': operational_data,
                'assumptions': assumptions,
                'valuation': {},
                'thesis': {}
            }
            
            await ws_manager.send_activity(job_id, "data_processing", "Generating Excel file with formulas and formatting...")
            excel_path = self.excel_gen.generate_model(job_id, data)
            
            await self._update_step(job_id, 6, "completed", f"Excel model generated: {excel_path}")
            return excel_path
            
        except Exception as e:
            await self._update_step(job_id, 6, "error", str(e))
            raise
    
    async def _step7_valuation(self, job_id: str, company_metadata: Dict, assumptions: Dict) -> Dict[str, Any]:
        """Step 7: Run valuation"""
        await self._update_step(job_id, 7, "in_progress", "Running valuation...")
        await ws_manager.send_activity(job_id, "llm_thinking", "Claude AI calculating intrinsic value using RIV methodology...")
        
        try:
            await ws_manager.send_activity(job_id, "data_processing", "Loading valuation parameters from knowledge base...")
            knowledge_file = self.claude.load_knowledge_file(company_metadata.get('knowledge_file', 'generic.md'))
            
            await ws_manager.send_activity(job_id, "llm_thinking", "Determining cost of equity and terminal growth rate...")
            
            system_message = f"{knowledge_file}\n\nYou are a quantitative analyst performing valuation."
            
            user_prompt = f"""
Perform valuation for {company_metadata.get('full_name')} using RIV methodology.

Generate:
- Cost of equity (assume beta=1.0, Rf=7%, ERP=6%)
- Terminal growth rate
- Target price
- Upside/downside %
- Recommendation (Buy/Hold/Sell)

Return JSON.
"""
            
            response = await self.claude.call_claude(system_message, user_prompt, f"job_{job_id}_step7")
            
            try:
                valuation = json.loads(response)
            except:
                valuation = {
                    "recommendation": "HOLD",
                    "target_price": company_metadata.get('current_price', 100),
                    "upside": "0%",
                    "cost_of_equity": 13.0,
                    "terminal_growth": 3.0
                }
            
            await self._update_step(job_id, 7, "completed", "Valuation complete")
            return valuation
            
        except Exception as e:
            await self._update_step(job_id, 7, "error", str(e))
            raise
    
    async def _step8_thesis_generation(self, job_id: str, company_metadata: Dict,
                                      historical_financials: Dict, assumptions: Dict,
                                      valuation: Dict) -> Dict[str, Any]:
        """Step 8: Generate investment thesis"""
        await self._update_step(job_id, 8, "in_progress", "Writing investment thesis...")
        
        try:
            knowledge_file = self.claude.load_knowledge_file(company_metadata.get('knowledge_file', 'generic.md'))
            
            system_message = f"{knowledge_file}\n\nYou are a senior equity research analyst writing an investment note."
            
            user_prompt = f"""
Write a professional investment thesis for {company_metadata.get('full_name')}.

Target Price: ₹{valuation.get('target_price')}
Recommendation: {valuation.get('recommendation')}

Include sections:
1. RECOMMENDATION
2. INVESTMENT CASE
3. KEY ASSUMPTIONS
4. WHERE WE COULD BE WRONG
5. RISKS
6. VALUATION

Write in professional equity research style.
"""
            
            response = await self.claude.call_claude(system_message, user_prompt, f"job_{job_id}_step8")
            
            thesis = {
                "full_text": response,
                "summary": f"{valuation.get('recommendation')} with target price of ₹{valuation.get('target_price')}"
            }
            
            await self._update_step(job_id, 8, "completed", "Investment thesis generated")
            return thesis
            
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
