"""
Mosaic Agent Service

This module implements the agentic Claude loop that autonomously builds
financial models using the tool-use API via LiteLLM and Emergent's LLM gateway.

Optimizations:
- Uses fast model (Haiku) for tool selection, full model for final analysis
- Summarizes tool results to reduce context size
- Truncates financial data to recent 5 years
- Limits PDF text extraction
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

# Model configuration - use the available Sonnet model
# Haiku isn't available via Emergent gateway, so we use Sonnet with reduced tokens
FAST_MODEL = "claude-sonnet-4-5-20250929"  # Same model, but with lower tokens for speed
FULL_MODEL = "claude-sonnet-4-5-20250929"  # Full model for complex reasoning

# Context optimization settings
MAX_TOOL_RESULT_LENGTH = 2000  # Max chars per tool result in context
MAX_MESSAGES_BEFORE_SUMMARY = 15  # Summarize context after this many messages
MAX_RECENT_YEARS = 5  # Only keep recent 5 years of financial data

# Rate limiting / gateway relief settings
DELAY_BETWEEN_LLM_CALLS = 10  # Seconds to wait between LLM calls to avoid rate limits

# System prompt for the Mosaic agent
MOSAIC_SYSTEM_PROMPT = """You are Mosaic, an autonomous financial analyst specializing in Indian equities.

Given a stock ticker, your job is to:
1. Check cache first — use cache_read() to avoid redundant scraping
2. Gather financial data — get_screener_financials() and get_stock_price()
3. Retrieve sector knowledge — use get_sector_knowledge() with specific queries
4. Read 1-2 PDFs — prioritize the most recent investor presentation or concall
5. Analyze the data and store your analysis incrementally using store_analysis_data():
   - store_analysis_data("company_info", {sector, sub_sector, business_description})
   - store_analysis_data("assumptions", {growth_drivers: [{name, value, rationale}]})
   - store_analysis_data("valuation", {methodology, fair_value, target_price, recommendation, upside_percent})
   - store_analysis_data("thesis", {summary, bull_case, bear_case, catalysts})
   - store_analysis_data("management_commentary", {key_highlights, guidance, risks})
6. Generate the Excel model — call generate_excel_model(ticker, confirm_ready=true)
7. Update knowledge base — call update_sector_knowledge() with any new observations

CRITICAL: Store your analysis data INCREMENTALLY using store_analysis_data() before calling generate_excel_model(). This allows you to build the model step by step without hitting token limits.

IMPORTANT GUIDELINES:
- For banks/NBFCs: focus on NIM, CASA ratio, GNPA/NNPA, ROE, Credit Cost. Use Residual Income (RIV) valuation.
- For other sectors: focus on Revenue growth, EBITDA margins, ROCE, FCF generation. Use DCF valuation.
- Be concise in your tool arguments to avoid token limits
- If uncertain between data points, explain your choice
- Flag knowledge gaps using flag_knowledge_gap() when needed

After completing all tasks, provide a brief final summary with key findings and recommendation.
"""


class MosaicAgent:
    """Agentic Claude service for autonomous financial model building using LiteLLM"""
    
    def __init__(self, scraper_service, pdf_extractor, excel_generator, db=None):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment")
        
        self.tool_executor = ToolExecutor(scraper_service, pdf_extractor, excel_generator)
        self.db = db
        self._current_job_id = None
        self._current_ticker = None
        self._tool_calls_log = []
        self._collected_data = {}  # Store full data for Excel generation
    
    def _summarize_tool_result(self, tool_name: str, result: Dict) -> str:
        """Summarize tool result to reduce context size"""
        if not result.get("success", False):
            return json.dumps({"success": False, "error": result.get("error", "Unknown error")})
        
        # Store full data for later use
        if tool_name == "get_screener_financials":
            self._collected_data["financials"] = result
            # Return summary only
            return json.dumps({
                "success": True,
                "ticker": result.get("ticker"),
                "years_available": result.get("years_available", [])[-MAX_RECENT_YEARS:],
                "quarters_available": result.get("quarters_available", [])[-8:],
                "key_metrics_latest": self._extract_key_metrics(result),
                "note": "Full data stored. Use for write_excel_model."
            })
        
        elif tool_name == "get_stock_price":
            return json.dumps(result)  # Already small
        
        elif tool_name == "download_and_parse_pdf":
            self._collected_data.setdefault("pdfs", []).append(result)
            # Truncate PDF text significantly
            text = result.get("text", "")
            return json.dumps({
                "success": True,
                "doc_type": result.get("doc_type"),
                "text_length": len(text),
                "text_preview": text[:MAX_TOOL_RESULT_LENGTH] + ("..." if len(text) > MAX_TOOL_RESULT_LENGTH else ""),
                "key_sections": self._extract_pdf_key_sections(text)
            })
        
        elif tool_name == "get_sector_knowledge":
            # Keep knowledge responses but truncate if needed
            content = result.get("content", "")
            if len(content) > MAX_TOOL_RESULT_LENGTH:
                return json.dumps({
                    "success": True,
                    "sector": result.get("sector"),
                    "query": result.get("query"),
                    "content": content[:MAX_TOOL_RESULT_LENGTH] + "...[truncated]"
                })
            return json.dumps(result)
        
        elif tool_name == "get_peer_comparison":
            self._collected_data["peers"] = result
            # Summarize peers
            peers = result.get("peers", [])[:5]  # Top 5 only
            return json.dumps({
                "success": True,
                "ticker": result.get("ticker"),
                "sector": result.get("sector"),
                "peer_count": len(result.get("peers", [])),
                "top_peers": [p.get("name", p) if isinstance(p, dict) else p for p in peers]
            })
        
        else:
            # Default: truncate if too long
            result_str = json.dumps(result, default=str)
            if len(result_str) > MAX_TOOL_RESULT_LENGTH:
                return result_str[:MAX_TOOL_RESULT_LENGTH] + '..."}'
            return result_str
    
    def _extract_key_metrics(self, financials: Dict) -> Dict:
        """Extract key metrics from financials for summary"""
        metrics = {}
        pnl = financials.get("annual_pnl", {})
        ratios = financials.get("ratios", {})
        
        # Get latest year data
        years = sorted(pnl.keys())[-MAX_RECENT_YEARS:] if pnl else []
        if years:
            latest = years[-1]
            latest_pnl = pnl.get(latest, {})
            metrics["latest_year"] = latest
            metrics["revenue"] = latest_pnl.get("Sales", latest_pnl.get("Revenue", "N/A"))
            metrics["net_profit"] = latest_pnl.get("Net Profit", "N/A")
        
        # Key ratios
        if ratios:
            ratio_years = sorted(ratios.keys())[-1:] if ratios else []
            if ratio_years:
                latest_ratios = ratios.get(ratio_years[0], {})
                metrics["roe"] = latest_ratios.get("ROE", "N/A")
                metrics["roce"] = latest_ratios.get("ROCE", "N/A")
        
        return metrics
    
    def _extract_pdf_key_sections(self, text: str) -> List[str]:
        """Extract key section headers from PDF text"""
        keywords = ["outlook", "guidance", "growth", "strategy", "risk", "highlight", "performance", "margin"]
        lines = text.split('\n')
        key_sections = []
        for line in lines[:100]:  # Check first 100 lines
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in keywords) and len(line) < 100:
                key_sections.append(line.strip())
                if len(key_sections) >= 5:
                    break
        return key_sections
    
    def _call_llm_with_tools(self, messages: List[Dict], tools: List[Dict], use_fast_model: bool = True, max_retries: int = 3, high_tokens: bool = False) -> Dict:
        """
        Call LiteLLM with tools support via Emergent's LLM gateway.
        
        Args:
            messages: Conversation messages
            tools: Tool definitions
            use_fast_model: Use Haiku for speed, Sonnet for quality
            max_retries: Number of retry attempts
            high_tokens: Use higher token limit for complex operations like Excel generation
        
        Returns the raw response from litellm.completion()
        """
        model = FAST_MODEL if use_fast_model else FULL_MODEL
        max_tokens = 8192 if high_tokens else 4096  # Higher for Excel model generation
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    api_key=self.api_key,
                    api_base=EMERGENT_PROXY_URL,
                    custom_llm_provider="openai",
                    max_tokens=max_tokens,
                    timeout=90,  # Reduced timeout for faster fails
                )
                return response
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                # Retry on transient errors
                if any(x in error_str for x in ['502', '503', '504', 'timeout', 'connection', 'gateway']):
                    wait_time = (attempt + 1) * 5  # 5s, 10s, 15s backoff
                    logger.warning(f"LLM call attempt {attempt + 1} failed with transient error, retrying in {wait_time}s: {str(e)[:100]}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        # All retries failed
        raise last_error
    
    async def run_agent(self, ticker: str, job_id: str) -> Dict[str, Any]:
        """
        Run the agentic loop to build a complete financial model.
        
        Uses LiteLLM with Emergent's LLM gateway for tool-use capabilities.
        
        Args:
            ticker: Stock ticker to analyze
            job_id: Job ID for tracking and WebSocket updates
            
        Returns:
            Complete result including model path, thesis, and reasoning
        """
        self._current_job_id = job_id
        self._current_ticker = ticker
        self._tool_calls_log = []
        self._collected_data = {}  # Reset collected data
        
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

Build the complete financial model for {ticker}. Be efficient - gather data, analyze, and create the Excel model.
Note: Tool results are summarized. Full data is stored internally for write_excel_model().
"""
        
        # Initialize messages with system prompt (OpenAI format)
        messages = [
            {"role": "system", "content": MOSAIC_SYSTEM_PROMPT},
            {"role": "user", "content": primer}
        ]
        
        await ws_manager.send_activity(
            job_id, "agent_start", 
            f"🤖 Mosaic agent started analyzing {ticker} (fast mode)",
            {"ticker": ticker, "cached_keys": cache_summary}
        )
        
        # Agent loop
        loop_count = 0
        max_loops = 30  # Reduced from 50
        final_response = None
        excel_path = None
        needs_high_tokens = False  # Flag for when we need more output tokens
        
        try:
            while loop_count < max_loops:
                loop_count += 1
                
                # Use high tokens after loop 6 (likely building Excel model soon)
                # or if previous response was cut off (finish_reason=length)
                use_high_tokens = needs_high_tokens or loop_count > 6
                
                # Call LLM with tools via LiteLLM
                try:
                    logger.info(f"Agent loop {loop_count}: calling LLM with {len(messages)} messages (high_tokens={use_high_tokens})")
                    response = self._call_llm_with_tools(
                        messages, 
                        MOSAIC_TOOLS_OPENAI_FORMAT, 
                        use_fast_model=True,  # Always use fast model, just vary tokens
                        high_tokens=use_high_tokens
                    )
                except Exception as e:
                    logger.error(f"LLM API error: {str(e)}")
                    await ws_manager.send_activity(job_id, "error", f"LLM API error: {str(e)[:100]}")
                    raise
                
                # Extract the message from response (OpenAI format)
                choice = response.choices[0]
                assistant_message = choice.message
                finish_reason = choice.finish_reason
                
                logger.info(f"Agent loop {loop_count}: finish_reason={finish_reason}")
                
                # If response was cut off, flag to use higher tokens next time
                if finish_reason == "length":
                    needs_high_tokens = True
                    logger.warning("Response truncated (length), will use higher tokens next loop")
                
                # Check if we're done (no tool calls)
                if finish_reason == "stop" or not assistant_message.tool_calls:
                    # Extract final text response
                    final_response = assistant_message.content or ""
                    logger.info(f"Agent finished with response length: {len(final_response)}")
                    break
                
                # Handle tool calls (OpenAI format)
                if assistant_message.tool_calls:
                    # Add delay before next LLM call to avoid rate limits
                    if DELAY_BETWEEN_LLM_CALLS > 0:
                        logger.info(f"Waiting {DELAY_BETWEEN_LLM_CALLS}s before next LLM call...")
                        await ws_manager.send_activity(
                            job_id, "info", 
                            f"⏳ Pacing requests ({DELAY_BETWEEN_LLM_CALLS}s cooldown)..."
                        )
                        await asyncio.sleep(DELAY_BETWEEN_LLM_CALLS)
                    
                    # Add assistant message with tool calls to history
                    messages.append({
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in assistant_message.tool_calls
                        ]
                    })
                    
                    # Process each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_input = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_input = {}
                        tool_id = tool_call.id
                        
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
                        
                        # Add SUMMARIZED tool result to messages (reduces context size)
                        summarized_result = self._summarize_tool_result(tool_name, result)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": summarized_result
                        })
                
                else:
                    # No tool calls and not finished - unexpected state
                    logger.warning(f"Unexpected state: finish_reason={finish_reason}, no tool_calls")
                    final_response = assistant_message.content or ""
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
