"""
Mosaic Agent Tools Registry

This module defines all tools available to the Claude agent for building
financial models autonomously.
"""

import json
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)

# Tool definitions for Claude's tool-use API
MOSAIC_TOOLS = [
    # ============== DATA COLLECTION ==============
    {
        "name": "get_screener_financials",
        "description": "Scrapes Screener.in for P&L, balance sheet, ratios, and quarterly data for a given Indian stock ticker. Returns 12 years of annual data and 12 quarters of quarterly data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "NSE/BSE stock ticker (e.g., 'HDFCBANK', 'RELIANCE')"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_stock_price",
        "description": "Fetches current stock price, market cap, P/E ratio, and book value from Yahoo Finance. Use this for real-time pricing data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "NSE/BSE stock ticker"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_document_links",
        "description": "Returns URLs for investor presentations, annual reports, and concall transcripts from Screener.in's documents section.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "NSE/BSE stock ticker"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_peer_comparison",
        "description": "Returns sector peer comparison data including key metrics for comparable companies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "NSE/BSE stock ticker"
                }
            },
            "required": ["ticker"]
        }
    },
    
    # ============== PDF ANALYSIS ==============
    {
        "name": "download_and_parse_pdf",
        "description": "Downloads a PDF document and extracts text content. For annual reports, extracts first 50 pages. For other documents, extracts full content. Returns structured text for analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Direct URL to the PDF document"
                },
                "doc_type": {
                    "type": "string",
                    "enum": ["annual_report", "investor_presentation", "concall"],
                    "description": "Type of document being parsed"
                }
            },
            "required": ["url", "doc_type"]
        }
    },
    
    # ============== KNOWLEDGE BASE ==============
    {
        "name": "get_sector_knowledge",
        "description": "Retrieves relevant chunks from the sector knowledge file based on a specific query. Returns only the most relevant sections, not the entire document. Use specific queries like 'NIM benchmarks' or 'valuation methodology'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": "Sector name (e.g., 'banks', 'nbfc', 'it', 'generic')"
                },
                "query": {
                    "type": "string",
                    "description": "Specific query to search for in the knowledge base (e.g., 'NIM benchmarks for private banks', 'credit cost norms')"
                }
            },
            "required": ["sector", "query"]
        }
    },
    {
        "name": "update_sector_knowledge",
        "description": "Appends a new observation or benchmark to the sector knowledge file. Use this to record new data points discovered during analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": "Sector name"
                },
                "finding": {
                    "type": "string",
                    "description": "The observation to record (e.g., 'NIM = 3.8%, GNPA = 1.2%')"
                },
                "source_ticker": {
                    "type": "string",
                    "description": "Ticker that this observation came from"
                },
                "source_doc": {
                    "type": "string",
                    "description": "Document source (e.g., 'Q4 FY25 concall', 'Annual Report FY25')"
                }
            },
            "required": ["sector", "finding", "source_ticker"]
        }
    },
    {
        "name": "flag_knowledge_gap",
        "description": "Flags a gap in the knowledge base when you lack sufficient information to make a well-grounded assumption. This helps identify areas needing human review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": "Sector name"
                },
                "missing_topic": {
                    "type": "string",
                    "description": "Description of the missing knowledge (e.g., 'credit cost norms for gold loan NBFCs')"
                }
            },
            "required": ["sector", "missing_topic"]
        }
    },
    
    # ============== MODEL OUTPUT ==============
    {
        "name": "store_analysis_data",
        "description": "Stores a piece of analyzed data for the final Excel model. Call this multiple times to build up the model data incrementally. Keys: 'company_info', 'valuation', 'assumptions', 'thesis', 'management_commentary'. Each call stores one piece.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "enum": ["company_info", "valuation", "assumptions", "thesis", "management_commentary"],
                    "description": "Type of data being stored"
                },
                "data": {
                    "type": "object",
                    "description": "The data to store. For company_info: {sector, sub_sector, business_description}. For valuation: {methodology, fair_value, target_price, recommendation, upside_percent}. For assumptions: {growth_drivers: [{name, value, rationale}]}. For thesis: {summary, bull_case, bear_case, catalysts}. For management_commentary: {key_highlights, guidance, risks}."
                }
            },
            "required": ["data_type", "data"]
        }
    },
    {
        "name": "generate_excel_model",
        "description": "Generates the final Excel model using all collected data (financials, PDFs, analysis stored via store_analysis_data). Call this AFTER you have: 1) scraped financials, 2) read at least one PDF, 3) stored company_info, valuation, assumptions, thesis via store_analysis_data. The tool will use internally collected data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker for the model"
                },
                "confirm_ready": {
                    "type": "boolean",
                    "description": "Set to true to confirm you have gathered all necessary data"
                }
            },
            "required": ["ticker", "confirm_ready"]
        }
    },
    {
        "name": "cache_read",
        "description": "Reads a cached result for a ticker. Use this to check if data has already been scraped before making redundant API calls.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker"
                },
                "key": {
                    "type": "string",
                    "description": "Cache key (e.g., 'screener_financials', 'stock_price', 'document_links', 'pdf_data', 'peer_comparison')"
                }
            },
            "required": ["ticker", "key"]
        }
    },
    {
        "name": "cache_write",
        "description": "Writes data to the cache for future reuse.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker"
                },
                "key": {
                    "type": "string",
                    "description": "Cache key"
                },
                "data": {
                    "type": "object",
                    "description": "Data to cache"
                }
            },
            "required": ["ticker", "key", "data"]
        }
    }
]


def _convert_to_openai_format(anthropic_tool: Dict) -> Dict:
    """Convert Anthropic tool format to OpenAI function calling format"""
    return {
        "type": "function",
        "function": {
            "name": anthropic_tool["name"],
            "description": anthropic_tool["description"],
            "parameters": anthropic_tool["input_schema"]
        }
    }


# OpenAI-format tools for LiteLLM (which uses OpenAI's tool format)
MOSAIC_TOOLS_OPENAI_FORMAT = [_convert_to_openai_format(tool) for tool in MOSAIC_TOOLS]


# Human-readable labels for frontend display
TOOL_LABELS = {
    "get_screener_financials": "📊 Pulling financial statements from Screener...",
    "get_stock_price": "💰 Fetching current stock price...",
    "get_document_links": "📑 Getting document links from Screener...",
    "get_peer_comparison": "👥 Fetching peer comparison data...",
    "download_and_parse_pdf": "📄 Reading {doc_type}: {url}...",
    "get_sector_knowledge": "🧠 Retrieving sector knowledge: '{query}'...",
    "update_sector_knowledge": "✍️ Updating knowledge base with new observation...",
    "flag_knowledge_gap": "⚠️ Knowledge gap flagged: {missing_topic}",
    "store_analysis_data": "💾 Storing {data_type} analysis...",
    "generate_excel_model": "📁 Building Excel model...",
    "cache_read": "📂 Checking cache for {key}...",
    "cache_write": "💾 Caching {key}..."
}


def get_tool_label(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Generate human-readable label for a tool call"""
    template = TOOL_LABELS.get(tool_name, f"🔧 Calling {tool_name}...")
    
    try:
        if tool_name == "download_and_parse_pdf":
            url = tool_input.get("url", "")
            filename = url.split("/")[-1][:30] if url else "document"
            return template.format(doc_type=tool_input.get("doc_type", "document"), url=filename)
        elif tool_name == "get_sector_knowledge":
            return template.format(query=tool_input.get("query", "")[:50])
        elif tool_name == "flag_knowledge_gap":
            return template.format(missing_topic=tool_input.get("missing_topic", "")[:50])
        elif tool_name in ["cache_read", "cache_write"]:
            return template.format(key=tool_input.get("key", "data"))
        else:
            return template
    except Exception:
        return f"🔧 Calling {tool_name}..."


class ToolExecutor:
    """Executes tools called by the Claude agent"""
    
    def __init__(self, scraper_service, pdf_extractor, excel_generator):
        self.scraper = scraper_service
        self.pdf_extractor = pdf_extractor
        self.excel_generator = excel_generator
        self.cache_dir = Path("/app/cached_data")
        self.knowledge_dir = Path("/app/knowledge")
        self.gaps_file = Path("/app/knowledge/knowledge_gaps.json")
        self._current_ticker = None
        self._current_job_id = None
        self._collected_data = {}  # Shared storage for incremental data collection
    
    def set_context(self, ticker: str, job_id: str):
        """Set current context for tool execution"""
        self._current_ticker = ticker
        self._current_job_id = job_id
        self._collected_data = {}  # Reset on new job
    
    def store_collected_data(self, key: str, data: Any):
        """Store data collected by agent (called from mosaic_agent.py)"""
        self._collected_data[key] = data
    
    async def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results"""
        start_time = datetime.now(timezone.utc)
        
        try:
            if tool_name == "get_screener_financials":
                result = await self._get_screener_financials(tool_input["ticker"])
            elif tool_name == "get_stock_price":
                result = await self._get_stock_price(tool_input["ticker"])
            elif tool_name == "get_document_links":
                result = await self._get_document_links(tool_input["ticker"])
            elif tool_name == "get_peer_comparison":
                result = await self._get_peer_comparison(tool_input["ticker"])
            elif tool_name == "download_and_parse_pdf":
                result = await self._download_and_parse_pdf(tool_input["url"], tool_input["doc_type"])
            elif tool_name == "get_sector_knowledge":
                result = self._get_sector_knowledge(tool_input["sector"], tool_input["query"])
            elif tool_name == "update_sector_knowledge":
                result = self._update_sector_knowledge(
                    tool_input["sector"],
                    tool_input["finding"],
                    tool_input["source_ticker"],
                    tool_input.get("source_doc", "analysis")
                )
            elif tool_name == "flag_knowledge_gap":
                result = self._flag_knowledge_gap(tool_input["sector"], tool_input["missing_topic"])
            elif tool_name == "store_analysis_data":
                result = self._store_analysis_data(tool_input["data_type"], tool_input["data"])
            elif tool_name == "generate_excel_model":
                result = await self._generate_excel_model(tool_input["ticker"], tool_input.get("confirm_ready", False))
            elif tool_name == "cache_read":
                result = self._cache_read(tool_input["ticker"], tool_input["key"])
            elif tool_name == "cache_write":
                result = self._cache_write(tool_input["ticker"], tool_input["key"], tool_input["data"])
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            
            # Log execution time
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Tool {tool_name} executed in {elapsed:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {str(e)}")
            return {"error": str(e), "tool": tool_name}
    
    # ============== DATA COLLECTION TOOLS ==============
    
    async def _get_screener_financials(self, ticker: str) -> Dict[str, Any]:
        """Scrape P&L, BS, and quarterly data from Screener.in"""
        try:
            # Get annual data
            annual_data = await self.scraper.scrape_annual_financials(ticker)
            
            # Get quarterly data
            quarterly_data = await self.scraper.scrape_quarterly_results(ticker)
            
            # Truncate to recent 5 years only
            def truncate_dict(d, max_items: int = 5):
                if not d:
                    return d if isinstance(d, dict) else {}
                if isinstance(d, list):
                    return d[-max_items:]  # Take last N items from list
                if isinstance(d, dict):
                    keys = sorted(d.keys())[-max_items:]
                    return {k: d[k] for k in keys}
                return d
            
            annual_pnl = truncate_dict(annual_data.get("annual_pnl", {}), 5)
            annual_bs = truncate_dict(annual_data.get("annual_bs", {}), 5)
            ratios = truncate_dict(annual_data.get("ratios", {}), 5)
            
            # Quarterly data might be a list or dict
            quarterly_raw = quarterly_data.get("quarters", {})
            if isinstance(quarterly_raw, list):
                # Convert list to dict format or just take the list
                quarterly = quarterly_raw[-8:]  # Last 8 quarters
            else:
                quarterly = truncate_dict(quarterly_raw, 8)
            
            result = {
                "success": True,
                "ticker": ticker,
                "annual_pnl": annual_pnl,
                "annual_bs": annual_bs,
                "ratios": ratios,
                "quarterly": quarterly,
                "years_available": list(annual_pnl.keys()) if isinstance(annual_pnl, dict) else [],
                "quarters_available": list(quarterly.keys()) if isinstance(quarterly, dict) else quarterly
            }
            
            logger.info(f"Scraped financials for {ticker}: pnl_years={list(annual_pnl.keys()) if isinstance(annual_pnl, dict) else 'N/A'}")
            
            # Auto-cache the result for Excel generation
            self._cache_write(ticker, "screener_financials", result)
            
            # Also store in collected_data for immediate use
            self._collected_data["financials"] = result
            logger.info(f"Stored financials in _collected_data, keys now: {list(self._collected_data.keys())}")
            
            return result
        except Exception as e:
            logger.error(f"Failed to get screener financials: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _get_stock_price(self, ticker: str) -> Dict[str, Any]:
        """Get current stock price from Yahoo Finance"""
        try:
            result = await self.scraper.get_current_market_price(ticker)
            stock_data = {
                "success": True,
                "ticker": ticker,
                "current_price": result.get("current_price"),
                "market_cap": result.get("market_cap"),
                "market_cap_cr": result.get("market_cap"),
                "pe_ratio": result.get("pe_ratio"),
                "book_value": result.get("book_value"),
                "source": result.get("source", "yahoo_finance"),
                "fetched_at": result.get("price_fetched_at")
            }
            
            # Auto-cache and store
            self._cache_write(ticker, "stock_price", stock_data)
            self._collected_data["stock_price"] = stock_data
            
            return stock_data
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_document_links(self, ticker: str) -> Dict[str, Any]:
        """Get document links from Screener.in and BSE"""
        try:
            docs = await self.scraper.scrape_investor_documents(ticker)
            return {
                "success": True,
                "ticker": ticker,
                "investor_presentations": docs.get("investor_presentations", [])[:5],
                "annual_reports": docs.get("annual_reports", [])[:3],
                "concall_transcripts": docs.get("concall_transcripts", [])[:4],
                "total_documents": len(docs.get("investor_presentations", [])) + 
                                   len(docs.get("annual_reports", [])) + 
                                   len(docs.get("concall_transcripts", []))
            }
        except Exception as e:
            logger.error(f"Failed to get document links for {ticker}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _get_peer_comparison(self, ticker: str) -> Dict[str, Any]:
        """Get peer comparison data"""
        try:
            data = await self.scraper.scrape_enhanced_data(ticker)
            return {
                "success": True,
                "ticker": ticker,
                "peers": data.get("peer_comparison", []),
                "sector": data.get("sector", "Unknown")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============== PDF ANALYSIS TOOLS ==============
    
    async def _download_and_parse_pdf(self, url: str, doc_type: str) -> Dict[str, Any]:
        """Download and parse PDF document"""
        try:
            # Reduced max pages for faster processing
            max_pages = 30 if doc_type == "annual_report" else 50
            
            # Download PDF
            filename = f"{doc_type}_{hash(url) % 100000}.pdf"
            filepath = self.pdf_extractor.download_pdf(url, filename)
            
            if not filepath:
                return {"success": False, "error": "Failed to download PDF"}
            
            # Extract text
            text = self.pdf_extractor.extract_text_from_pdf(filepath, max_pages=max_pages)
            
            if not text or len(text) < 500:
                return {"success": False, "error": "PDF text extraction yielded insufficient content"}
            
            # Clean up downloaded file
            try:
                os.remove(filepath)
            except:
                pass
            
            # Limit text to 20k chars (reduced from 50k)
            max_text_length = 20000
            return {
                "success": True,
                "doc_type": doc_type,
                "url": url,
                "text_length": len(text),
                "text": text[:max_text_length],
                "truncated": len(text) > max_text_length
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============== KNOWLEDGE BASE TOOLS ==============
    
    def _get_sector_knowledge(self, sector: str, query: str) -> Dict[str, Any]:
        """Get relevant knowledge chunks based on query"""
        try:
            # Map sector to filename
            sector_lower = sector.lower().strip()
            if sector_lower in ["bank", "banks", "banking"]:
                filename = "banks.md"
            elif sector_lower in ["nbfc", "finance", "financial services"]:
                filename = "nbfc.md" if (self.knowledge_dir / "nbfc.md").exists() else "banks.md"
            else:
                filename = f"{sector_lower}.md"
            
            filepath = self.knowledge_dir / filename
            if not filepath.exists():
                filepath = self.knowledge_dir / "generic.md"
            
            content = filepath.read_text()
            
            # Split by ## headers for chunking
            chunks = self._chunk_by_headers(content)
            
            # Score and rank chunks by relevance to query
            scored_chunks = []
            query_terms = set(query.lower().split())
            
            for header, chunk_text in chunks:
                # Simple keyword overlap scoring
                chunk_terms = set(chunk_text.lower().split())
                overlap = len(query_terms & chunk_terms)
                # Boost if query terms appear in header
                header_terms = set(header.lower().split())
                header_boost = len(query_terms & header_terms) * 3
                score = overlap + header_boost
                
                if score > 0:
                    scored_chunks.append((score, header, chunk_text))
            
            # Sort by score and return top 3
            scored_chunks.sort(reverse=True, key=lambda x: x[0])
            top_chunks = scored_chunks[:3]
            
            return {
                "success": True,
                "sector": sector,
                "query": query,
                "source_file": filename,
                "chunks": [
                    {"header": h, "content": c[:2000], "relevance_score": s}
                    for s, h, c in top_chunks
                ],
                "total_chunks_found": len(scored_chunks)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _chunk_by_headers(self, content: str) -> List[tuple]:
        """Split markdown content by ## headers"""
        chunks = []
        current_header = "Introduction"
        current_content = []
        
        for line in content.split("\n"):
            if line.startswith("## "):
                if current_content:
                    chunks.append((current_header, "\n".join(current_content)))
                current_header = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        if current_content:
            chunks.append((current_header, "\n".join(current_content)))
        
        return chunks
    
    def _update_sector_knowledge(self, sector: str, finding: str, source_ticker: str, source_doc: str = "analysis") -> Dict[str, Any]:
        """Update sector knowledge with new observation"""
        try:
            # Map sector to filename
            sector_lower = sector.lower().strip()
            if sector_lower in ["bank", "banks", "banking"]:
                filename = "banks.md"
            else:
                filename = f"{sector_lower}.md"
            
            filepath = self.knowledge_dir / filename
            if not filepath.exists():
                return {"success": False, "error": f"Knowledge file {filename} not found"}
            
            content = filepath.read_text()
            
            # Find or create "## Observed Data" section
            observed_header = "## Observed Data (Auto-updated by Mosaic)"
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # Get fiscal year
            current_month = datetime.now().month
            fy_year = datetime.now().year if current_month >= 4 else datetime.now().year - 1
            
            new_entry = f"- {source_ticker} FY{fy_year % 100 + 1}: {finding} (source: {source_doc}, added: {timestamp})"
            
            if observed_header in content:
                # Append to existing section
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.strip() == observed_header:
                        # Insert after header
                        lines.insert(i + 1, new_entry)
                        break
                content = "\n".join(lines)
            else:
                # Add new section at end
                content += f"\n\n{observed_header}\n{new_entry}\n"
            
            filepath.write_text(content)
            
            return {
                "success": True,
                "sector": sector,
                "entry_added": new_entry,
                "file_updated": filename
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _flag_knowledge_gap(self, sector: str, missing_topic: str) -> Dict[str, Any]:
        """Flag a knowledge gap for human review"""
        try:
            # Load existing gaps
            gaps = []
            if self.gaps_file.exists():
                try:
                    gaps = json.loads(self.gaps_file.read_text())
                except:
                    gaps = []
            
            # Add new gap
            gap_entry = {
                "sector": sector,
                "missing_topic": missing_topic,
                "flagged_by": self._current_ticker or "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            gaps.append(gap_entry)
            
            # Save
            self.gaps_file.parent.mkdir(parents=True, exist_ok=True)
            self.gaps_file.write_text(json.dumps(gaps, indent=2))
            
            return {
                "success": True,
                "gap_logged": gap_entry,
                "total_gaps": len(gaps)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============== MODEL OUTPUT TOOLS ==============
    
    def _store_analysis_data(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a piece of analysis data for later Excel generation"""
        try:
            valid_types = ["company_info", "valuation", "assumptions", "thesis", "management_commentary"]
            if data_type not in valid_types:
                return {"success": False, "error": f"Invalid data_type. Must be one of: {valid_types}"}
            
            # Store in the shared collected_data dict
            self._collected_data[data_type] = data
            
            stored_keys = list(self._collected_data.keys())
            
            return {
                "success": True,
                "stored": data_type,
                "all_stored_types": stored_keys,
                "ready_for_excel": all(k in stored_keys for k in ["company_info", "valuation", "assumptions", "thesis"])
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_excel_model(self, ticker: str, confirm_ready: bool) -> Dict[str, Any]:
        """Generate the complete Excel model using all collected data"""
        try:
            if not confirm_ready:
                return {
                    "success": False, 
                    "error": "Set confirm_ready=true to generate the model",
                    "hint": "Make sure you have stored company_info, valuation, assumptions, thesis first"
                }
            
            # Check what data we have collected
            collected = self._collected_data
            logger.info(f"Collected data keys: {list(collected.keys())}")
            
            required = ["company_info", "valuation", "assumptions", "thesis"]
            missing = [k for k in required if k not in collected]
            
            if missing:
                return {
                    "success": False,
                    "error": f"Missing required data: {missing}",
                    "hint": "Use store_analysis_data to store these before generating Excel"
                }
            
            # Get financials from collected data or cache
            financials = collected.get("financials", {})
            logger.info(f"Financials from collected: {bool(financials)}, keys: {list(financials.keys()) if financials else []}")
            
            if not financials or not financials.get("annual_pnl"):
                # Try to load from cache
                cache_result = self._cache_read(self._current_ticker, "screener_financials")
                logger.info(f"Cache result: cached={cache_result.get('cached')}")
                if cache_result.get("cached"):
                    financials = cache_result.get("data", {})
                    logger.info(f"Financials from cache: {list(financials.keys()) if financials else []}")
            
            # Get stock price
            stock_price = collected.get("stock_price", {})
            if not stock_price:
                cache_result = self._cache_read(ticker, "stock_price")
                if cache_result.get("cached"):
                    stock_price = cache_result.get("data", {})
            
            # Get peer data
            peers = collected.get("peers", {})
            if not peers:
                cache_result = self._cache_read(ticker, "peer_comparison")
                if cache_result.get("cached"):
                    peers = cache_result.get("data", {})
            
            # Build the model_data structure for Excel generator
            logger.info(f"Building model_data with financials keys: {list(financials.keys())}")
            logger.info(f"annual_pnl sample: {list(financials.get('annual_pnl', {}).keys())[:3]}")
            
            model_data = {
                "company_metadata": {
                    "ticker": ticker,
                    "name": financials.get("company_name", ticker),
                    "sector": collected.get("company_info", {}).get("sector", "Unknown"),
                    "sub_sector": collected.get("company_info", {}).get("sub_sector", ""),
                    "current_price": stock_price.get("current_price", 0),
                    "market_cap": stock_price.get("market_cap", 0),
                    "pe_ratio": stock_price.get("pe_ratio", 0),
                    "book_value": stock_price.get("book_value", 0),
                    "business_description": collected.get("company_info", {}).get("business_description", "")
                },
                "historical_financials": {
                    "annual_pnl": financials.get("annual_pnl", {}),
                    "annual_bs": financials.get("annual_bs", {}),
                    "ratios": financials.get("ratios", {})
                },
                "quarterly_results": financials.get("quarterly", {}),
                "assumptions": collected.get("assumptions", {}),
                "valuation": collected.get("valuation", {}),
                "thesis": collected.get("thesis", {}),
                "management_commentary": collected.get("management_commentary", {}),
                "peer_comparison": peers.get("peers", []) if isinstance(peers, dict) else []
            }
            
            # Generate the Excel file
            job_id = self._current_job_id or "manual"
            excel_path = self.excel_generator.generate_model(job_id, model_data)
            
            return {
                "success": True,
                "file_path": excel_path,
                "sheets_created": [
                    "Cover", "Assumptions", "P&L", "Balance Sheet", 
                    "ROE Tree", "Quarterly", "Key Ratios", "Valuation",
                    "Peer Comparison", "Thesis"
                ],
                "data_sources_used": list(collected.keys())
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _cache_read(self, ticker: str, key: str) -> Dict[str, Any]:
        """Read from cache"""
        try:
            cache_path = self.cache_dir / ticker / f"{key}.json"
            
            if not cache_path.exists():
                return {"success": True, "cached": False, "data": None}
            
            data = json.loads(cache_path.read_text())
            
            # Check if cache has actual data
            actual_data = data.get("data", data)
            
            return {
                "success": True,
                "cached": True,
                "data": actual_data,
                "cached_at": data.get("cached_at")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _cache_write(self, ticker: str, key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Write to cache"""
        try:
            cache_path = self.cache_dir / ticker / f"{key}.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            cache_entry = {
                "ticker": ticker,
                "key": key,
                "data": data,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
            
            cache_path.write_text(json.dumps(cache_entry, indent=2, default=str))
            
            return {
                "success": True,
                "cached_key": key,
                "file_path": str(cache_path)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_cache_summary(ticker: str) -> List[str]:
    """Get list of cached keys for a ticker"""
    cache_dir = Path("/app/cached_data") / ticker
    
    if not cache_dir.exists():
        return []
    
    cached_keys = []
    for f in cache_dir.glob("*.json"):
        cached_keys.append(f.stem)
    
    return cached_keys
