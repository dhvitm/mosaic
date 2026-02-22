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
        "name": "write_excel_model",
        "description": "Generates the complete multi-sheet Excel financial model. Takes fully populated structured data and creates formula-linked workbook with Cover, Assumptions, P&L, Balance Sheet, ROE Tree, Quarterly, Key Ratios, Valuation, Peer Comparison, and Thesis sheets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_data": {
                    "type": "object",
                    "description": "Complete model data including company_metadata, historical_financials, quarterly_results, assumptions, valuation, thesis, and peer_comparison"
                }
            },
            "required": ["model_data"]
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
    "write_excel_model": "📁 Building Excel model...",
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
    
    def set_context(self, ticker: str, job_id: str):
        """Set current context for tool execution"""
        self._current_ticker = ticker
        self._current_job_id = job_id
    
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
            elif tool_name == "write_excel_model":
                result = self._write_excel_model(tool_input["model_data"])
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
            
            return {
                "success": True,
                "ticker": ticker,
                "annual_pnl": annual_data.get("annual_pnl", {}),
                "annual_bs": annual_data.get("annual_bs", {}),
                "ratios": annual_data.get("ratios", {}),
                "quarterly": quarterly_data.get("quarters", {}),
                "years_available": list(annual_data.get("annual_pnl", {}).keys()),
                "quarters_available": list(quarterly_data.get("quarters", {}).keys())
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_stock_price(self, ticker: str) -> Dict[str, Any]:
        """Get current stock price from Yahoo Finance"""
        try:
            result = await self.scraper.get_current_market_price(ticker)
            return {
                "success": True,
                "ticker": ticker,
                "current_price": result.get("current_price"),
                "market_cap_cr": result.get("market_cap"),
                "pe_ratio": result.get("pe_ratio"),
                "book_value": result.get("book_value"),
                "source": result.get("source", "yahoo_finance"),
                "fetched_at": result.get("price_fetched_at")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_document_links(self, ticker: str) -> Dict[str, Any]:
        """Get document links from Screener.in"""
        try:
            docs = await self.scraper.scrape_screener_documents(ticker)
            return {
                "success": True,
                "ticker": ticker,
                "investor_presentations": docs.get("bse_presentations", [])[:5],
                "annual_reports": docs.get("annual_reports", [])[:3],
                "concall_transcripts": docs.get("transcripts", [])[:4],
                "total_documents": len(docs.get("bse_presentations", [])) + 
                                   len(docs.get("annual_reports", [])) + 
                                   len(docs.get("transcripts", []))
            }
        except Exception as e:
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
            # Determine max pages based on doc type
            max_pages = 50 if doc_type == "annual_report" else 100
            
            # Download PDF
            filename = f"{doc_type}_{hash(url) % 100000}.pdf"
            filepath = self.pdf_extractor.download_pdf(url, filename)
            
            if not filepath:
                return {"success": False, "error": "Failed to download PDF"}
            
            # Extract text
            text = self.pdf_extractor.extract_text_from_pdf(filepath, max_pages=max_pages)
            
            if not text or len(text) < 1000:
                return {"success": False, "error": "PDF text extraction yielded insufficient content"}
            
            # Clean up downloaded file
            try:
                os.remove(filepath)
            except:
                pass
            
            return {
                "success": True,
                "doc_type": doc_type,
                "url": url,
                "text_length": len(text),
                "text": text[:50000],  # Limit to 50k chars for Claude context
                "truncated": len(text) > 50000
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
    
    def _write_excel_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the complete Excel model"""
        try:
            job_id = self._current_job_id or "manual"
            excel_path = self.excel_generator.generate_model(job_id, model_data)
            
            return {
                "success": True,
                "file_path": excel_path,
                "sheets_created": [
                    "Cover", "Assumptions", "P&L", "Balance Sheet", 
                    "ROE Tree", "Quarterly", "Key Ratios", "Valuation",
                    "Peer Comparison", "Thesis"
                ]
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
