"""
LLM Logger Service

Captures all LLM calls and responses for debugging and analysis.
Logs are stored per job/ticker in JSON format.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Directory for LLM logs
LLM_LOGS_DIR = Path("/app/backend/logs/llm")
LLM_LOGS_DIR.mkdir(parents=True, exist_ok=True)


class LLMLogger:
    """Logger for capturing LLM calls and responses per job."""
    
    def __init__(self, job_id: str, ticker: str):
        self.job_id = job_id
        self.ticker = ticker
        self.log_file = LLM_LOGS_DIR / f"{ticker}_{job_id}.json"
        self.interactions: List[Dict[str, Any]] = []
        self.start_time = datetime.now(timezone.utc)
        
        # Initialize log file
        self._init_log()
    
    def _init_log(self):
        """Initialize the log file with metadata."""
        metadata = {
            "job_id": self.job_id,
            "ticker": self.ticker,
            "started_at": self.start_time.isoformat(),
            "interactions": []
        }
        self._write_log(metadata)
        logger.info(f"LLM Logger initialized for {self.ticker} (job: {self.job_id})")
    
    def _write_log(self, data: Dict[str, Any]):
        """Write log data to file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to write LLM log: {e}")
    
    def _read_log(self) -> Dict[str, Any]:
        """Read current log data."""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read LLM log: {e}")
        return {"interactions": []}
    
    def log_llm_call(
        self,
        loop_number: int,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict]] = None
    ):
        """Log an LLM API call (request)."""
        interaction = {
            "type": "llm_call",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "loop_number": loop_number,
            "model": model,
            "message_count": len(messages),
            "messages": self._sanitize_messages(messages),
            "tools_available": [t.get("function", {}).get("name") for t in (tools or [])] if tools else []
        }
        self._append_interaction(interaction)
    
    def log_llm_response(
        self,
        loop_number: int,
        response: Dict[str, Any],
        finish_reason: str,
        tool_calls: Optional[List[Dict]] = None,
        response_text: Optional[str] = None
    ):
        """Log an LLM API response."""
        interaction = {
            "type": "llm_response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "loop_number": loop_number,
            "finish_reason": finish_reason,
            "tool_calls": self._sanitize_tool_calls(tool_calls) if tool_calls else None,
            "response_text": response_text[:2000] if response_text else None,  # Truncate long responses
            "usage": response.get("usage") if isinstance(response, dict) else None
        }
        self._append_interaction(interaction)
    
    def log_tool_execution(
        self,
        loop_number: int,
        tool_name: str,
        tool_id: str,
        arguments: Dict[str, Any],
        result: Any,
        duration_ms: Optional[float] = None
    ):
        """Log a tool execution."""
        interaction = {
            "type": "tool_execution",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "loop_number": loop_number,
            "tool_name": tool_name,
            "tool_id": tool_id,
            "arguments": arguments,
            "result_summary": self._summarize_result(result),
            "duration_ms": duration_ms
        }
        self._append_interaction(interaction)
    
    def log_error(self, loop_number: int, error: str, context: Optional[str] = None):
        """Log an error."""
        interaction = {
            "type": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "loop_number": loop_number,
            "error": error,
            "context": context
        }
        self._append_interaction(interaction)
    
    def log_completion(self, success: bool, final_result: Optional[Dict] = None):
        """Log job completion."""
        interaction = {
            "type": "completion",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "duration_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "total_interactions": len(self.interactions),
            "result_summary": self._summarize_result(final_result) if final_result else None
        }
        self._append_interaction(interaction)
    
    def _append_interaction(self, interaction: Dict[str, Any]):
        """Append an interaction to the log."""
        self.interactions.append(interaction)
        
        # Update log file
        log_data = self._read_log()
        log_data["interactions"] = self.interactions
        log_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._write_log(log_data)
    
    def _sanitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize messages for logging (truncate long content)."""
        sanitized = []
        for msg in messages:
            clean_msg = {
                "role": msg.get("role"),
            }
            content = msg.get("content")
            if isinstance(content, str):
                clean_msg["content"] = content[:1000] + "..." if len(content) > 1000 else content
            elif isinstance(content, list):
                # Handle multi-part content
                clean_msg["content"] = f"[{len(content)} parts]"
            else:
                clean_msg["content"] = str(content)[:500] if content else None
            
            # Include tool_calls if present
            if "tool_calls" in msg:
                clean_msg["tool_calls"] = self._sanitize_tool_calls(msg["tool_calls"])
            
            sanitized.append(clean_msg)
        return sanitized
    
    def _sanitize_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """Sanitize tool calls for logging."""
        if not tool_calls:
            return []
        sanitized = []
        for tc in tool_calls:
            if hasattr(tc, 'function'):
                # LiteLLM response object
                sanitized.append({
                    "id": tc.id if hasattr(tc, 'id') else None,
                    "name": tc.function.name if hasattr(tc.function, 'name') else None,
                    "arguments": tc.function.arguments[:500] if hasattr(tc.function, 'arguments') else None
                })
            elif isinstance(tc, dict):
                func = tc.get("function", {})
                sanitized.append({
                    "id": tc.get("id"),
                    "name": func.get("name") if isinstance(func, dict) else None,
                    "arguments": str(func.get("arguments", ""))[:500] if isinstance(func, dict) else None
                })
        return sanitized
    
    def _summarize_result(self, result: Any) -> str:
        """Create a summary of a result for logging."""
        if result is None:
            return "None"
        if isinstance(result, str):
            return result[:500] + "..." if len(result) > 500 else result
        if isinstance(result, dict):
            keys = list(result.keys())
            return f"Dict with keys: {keys[:10]}"
        if isinstance(result, list):
            return f"List with {len(result)} items"
        return str(result)[:500]


def get_logs_for_ticker(ticker: str) -> List[Dict[str, Any]]:
    """Get all logs for a specific ticker."""
    logs = []
    for log_file in LLM_LOGS_DIR.glob(f"{ticker}_*.json"):
        try:
            with open(log_file, 'r') as f:
                logs.append(json.load(f))
        except Exception as e:
            logger.error(f"Failed to read log file {log_file}: {e}")
    
    # Sort by start time (most recent first)
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return logs


def get_log_for_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get log for a specific job."""
    for log_file in LLM_LOGS_DIR.glob(f"*_{job_id}.json"):
        try:
            with open(log_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read log file {log_file}: {e}")
    return None


def list_all_logs() -> List[Dict[str, Any]]:
    """List all available logs (metadata only)."""
    logs = []
    for log_file in LLM_LOGS_DIR.glob("*.json"):
        try:
            with open(log_file, 'r') as f:
                data = json.load(f)
                logs.append({
                    "job_id": data.get("job_id"),
                    "ticker": data.get("ticker"),
                    "started_at": data.get("started_at"),
                    "interaction_count": len(data.get("interactions", []))
                })
        except Exception as e:
            logger.error(f"Failed to read log file {log_file}: {e}")
    
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return logs
