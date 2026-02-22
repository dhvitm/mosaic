"""
Mosaic Agent Service

This module implements the agentic Claude loop that autonomously builds
financial models using the tool-use API via LiteLLM and Emergent's LLM gateway.
"""

import json
import os
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import litellm

from services.agent_tools import (
    MOSAIC_TOOLS, 
    MOSAIC_TOOLS_OPENAI_FORMAT,
    ToolExecutor, 
    get_tool_label, 
    get_cache_summary
)
from services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Emergent LLM Gateway URL
EMERGENT_PROXY_URL = "https://integrations.emergentagent.com/llm"

# System prompt for the Mosaic agent
MOSAIC_SYSTEM_PROMPT = """You are Mosaic, an autonomous financial analyst specializing in Indian equities.

Given a stock ticker, your job is to:
1. Gather all available financial data using your tools — start with screener financials and stock price
2. Check the cache before scraping — use cache_read() to avoid redundant calls
3. Retrieve relevant sector knowledge using get_sector_knowledge() with specific queries, not broad ones
4. Read at least 2 PDFs — prioritize the most recent concall and latest investor presentation
5. Cross-check data between sources — flag discrepancies rather than silently picking one
6. Generate 5-year forecast assumptions grounded in the data and management guidance
7. Run sector-appropriate valuation: Residual Income (RIV) for banks and NBFCs, DCF for others
8. Write a professional 400-500 word investment thesis
9. Call write_excel_model() with fully populated data — no placeholders
10. After completing the model, call update_sector_knowledge() with any new benchmarks or observations you discovered
11. If you lack sufficient sector context at any point, call flag_knowledge_gap() before making assumptions

Be explicit about your reasoning. State assumptions and their basis.
When uncertain between two data points, explain which you used and why.

IMPORTANT GUIDELINES:
- Always check cache first before making expensive API calls
- For banks/NBFCs, focus on: NIM, CASA ratio, GNPA/NNPA, ROE, Credit Cost
- For other sectors, focus on: Revenue growth, EBITDA margins, ROCE, FCF generation
- The model_data passed to write_excel_model() must include:
  - company_metadata: ticker, name, sector, current_price, market_cap
  - historical_financials: annual_pnl, annual_bs (keyed by year like "Mar 2024")
  - quarterly_results: quarters data
  - assumptions: 5-year forecast drivers with rationale
  - valuation: fair_value, recommendation, upside_percent, methodology
  - thesis: full investment thesis text
  - management_commentary: pros, cons, guidance, key_highlights

When you have gathered all data and are ready to build the model, structure model_data carefully with all required fields before calling write_excel_model().

After completing all tasks, provide a final summary of your analysis including:
- Key findings
- Assumptions made and their basis
- Any data discrepancies found
- Knowledge gaps flagged
"""


class MosaicAgent:
    """Agentic Claude service for autonomous financial model building using LiteLLM"""
    
    def __init__(self, scraper_service, pdf_extractor, excel_generator, db=None):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment")
        
        # Model to use (Claude Sonnet 4.5 via Emergent gateway)
        self.model = "claude-sonnet-4-5-20250929"
        
        self.tool_executor = ToolExecutor(scraper_service, pdf_extractor, excel_generator)
        self.db = db
        self._current_job_id = None
        self._current_ticker = None
        self._tool_calls_log = []
    
    def _call_llm_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """
        Call LiteLLM with tools support via Emergent's LLM gateway.
        
        Returns the raw response from litellm.completion()
        """
        response = litellm.completion(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            api_key=self.api_key,
            api_base=EMERGENT_PROXY_URL,
            custom_llm_provider="openai",
            max_tokens=8096,
        )
        return response
    
    async def run_agent(self, ticker: str, job_id: str) -> Dict[str, Any]:
        """
        Run the agentic loop to build a complete financial model.
        
        Args:
            ticker: Stock ticker to analyze
            job_id: Job ID for tracking and WebSocket updates
            
        Returns:
            Complete result including model path, thesis, and reasoning
        """
        self._current_job_id = job_id
        self._current_ticker = ticker
        self._tool_calls_log = []
        
        self.tool_executor.set_context(ticker, job_id)
        
        start_time = time.time()
        
        # Build context primer
        cache_summary = get_cache_summary(ticker)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        primer = f"""
Ticker: {ticker}
Previously cached data: {cache_summary if cache_summary else "None - fresh analysis required"}
Use cache_read() to retrieve any of these before scraping.

Today's date: {today}

Now build the complete financial model for {ticker}. Start by gathering data, then analyze, generate assumptions, run valuation, write thesis, and finally create the Excel model.
"""
        
        messages = [{"role": "user", "content": primer}]
        
        await ws_manager.send_activity(
            job_id, "agent_start", 
            f"🤖 Mosaic agent started analyzing {ticker}",
            {"ticker": ticker, "cached_keys": cache_summary}
        )
        
        # Agent loop
        loop_count = 0
        max_loops = 50  # Safety limit
        final_response = None
        excel_path = None
        
        try:
            while loop_count < max_loops:
                loop_count += 1
                
                # Call Claude with tools
                try:
                    response = self.client.messages.create(
                        model="claude-sonnet-4-5-20250929",
                        max_tokens=8096,
                        system=MOSAIC_SYSTEM_PROMPT,
                        tools=MOSAIC_TOOLS,
                        messages=messages
                    )
                except Exception as e:
                    logger.error(f"Claude API error: {str(e)}")
                    await ws_manager.send_activity(job_id, "error", f"Claude API error: {str(e)[:100]}")
                    raise
                
                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Extract final text response
                    for block in response.content:
                        if hasattr(block, 'text'):
                            final_response = block.text
                    break
                
                if response.stop_reason == "tool_use":
                    tool_results = []
                    
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_name = block.name
                            tool_input = block.input
                            tool_id = block.id
                            
                            # Log and broadcast tool call
                            label = get_tool_label(tool_name, tool_input)
                            await ws_manager.send_activity(job_id, "tool_call", label, {
                                "tool": tool_name,
                                "input_keys": list(tool_input.keys())
                            })
                            
                            # Execute tool
                            tool_start = time.time()
                            result = await self.tool_executor.execute(tool_name, tool_input)
                            tool_duration = time.time() - tool_start
                            
                            # Track Excel path
                            if tool_name == "write_excel_model" and result.get("success"):
                                excel_path = result.get("file_path")
                            
                            # Log tool call
                            tool_log = {
                                "tool": tool_name,
                                "input": tool_input,
                                "result_success": result.get("success", False),
                                "duration_seconds": round(tool_duration, 2),
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                            self._tool_calls_log.append(tool_log)
                            
                            # Broadcast result
                            status = "✓" if result.get("success", False) else "✗"
                            await ws_manager.send_activity(
                                job_id, "tool_result",
                                f"{status} {tool_name} completed ({tool_duration:.1f}s)",
                                {"success": result.get("success", False), "duration": tool_duration}
                            )
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(result, default=str)
                            })
                    
                    # Add assistant response and tool results to messages
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                
                else:
                    # Unknown stop reason
                    logger.warning(f"Unknown stop reason: {response.stop_reason}")
                    break
            
            elapsed = time.time() - start_time
            
            # Log tool calls to database
            if self.db:
                await self._log_tool_calls_to_db(job_id, self._tool_calls_log)
            
            await ws_manager.send_activity(
                job_id, "agent_complete",
                f"🎉 Analysis complete in {elapsed:.1f}s ({loop_count} iterations, {len(self._tool_calls_log)} tool calls)",
                {"elapsed_seconds": elapsed, "iterations": loop_count, "tool_calls": len(self._tool_calls_log)}
            )
            
            return {
                "success": True,
                "ticker": ticker,
                "excel_path": excel_path,
                "reasoning": final_response,
                "tool_calls": self._tool_calls_log,
                "iterations": loop_count,
                "elapsed_seconds": elapsed
            }
            
        except Exception as e:
            logger.error(f"Agent loop failed: {str(e)}")
            await ws_manager.send_activity(job_id, "error", f"Agent error: {str(e)[:200]}")
            
            return {
                "success": False,
                "ticker": ticker,
                "error": str(e),
                "tool_calls": self._tool_calls_log,
                "iterations": loop_count,
                "elapsed_seconds": time.time() - start_time
            }
    
    async def _log_tool_calls_to_db(self, job_id: str, tool_calls: List[Dict]):
        """Log tool calls to MongoDB for debugging"""
        try:
            if self.db:
                await self.db.model_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "tool_calls": tool_calls,
                        "tool_calls_count": len(tool_calls)
                    }}
                )
        except Exception as e:
            logger.error(f"Failed to log tool calls to DB: {str(e)}")
    
    def load_knowledge_file(self, filename: str) -> str:
        """Load a sector knowledge file (for backwards compatibility)"""
        knowledge_path = Path("/app/knowledge") / filename
        
        if not knowledge_path.exists():
            logger.warning(f"Knowledge file not found: {filename}, using generic.md")
            knowledge_path = Path("/app/knowledge/generic.md")
        
        return knowledge_path.read_text()
