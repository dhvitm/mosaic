from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
import time
from dotenv import load_dotenv
from pathlib import Path
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)

def is_retryable_error(exception):
    """Check if the error is retryable (502, 503, 504, timeout)"""
    error_str = str(exception).lower()
    return any(code in error_str for code in ['502', '503', '504', 'timeout', 'badgateway', 'service unavailable'])

class ClaudeService:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment")
        self._current_job_id = None  # Track current job for activity logging
    
    def set_job_id(self, job_id: str):
        """Set current job ID for activity logging"""
        self._current_job_id = job_id
    
    async def _broadcast_activity(self, activity_type: str, message: str, details: dict = None):
        """Broadcast activity to WebSocket if job_id is set"""
        if self._current_job_id:
            from services.websocket_manager import ws_manager
            await ws_manager.send_activity(self._current_job_id, activity_type, message, details)
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception(is_retryable_error),
        reraise=True
    )
    async def call_claude(self, system_message: str, user_prompt: str, session_id: str = "default") -> str:
        """
        Call Claude API with system message and user prompt.
        Retries on 502/503/504 errors with exponential backoff.
        """
        start_time = time.time()
        
        try:
            # Broadcast that we're starting the API call
            prompt_preview = user_prompt[:150] + "..." if len(user_prompt) > 150 else user_prompt
            await self._broadcast_activity(
                "api_call", 
                "Calling Claude API...",
                {"model": "claude-sonnet-4-5", "prompt_preview": prompt_preview}
            )
            
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_message
            )
            
            # Use Anthropic Claude Sonnet 4.5
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            
            await self._broadcast_activity("llm_thinking", "Claude is analyzing and generating response...")
            
            user_message = UserMessage(text=user_prompt)
            response = await chat.send_message(user_message)
            
            elapsed = round(time.time() - start_time, 2)
            response_preview = response[:100] + "..." if len(response) > 100 else response
            
            await self._broadcast_activity(
                "api_call", 
                f"Claude API response received ({elapsed}s)",
                {"elapsed_seconds": elapsed, "response_preview": response_preview}
            )
            
            logger.info(f"Claude API call successful for session: {session_id} ({elapsed}s)")
            return response
            
        except Exception as e:
            error_msg = str(e)
            elapsed = round(time.time() - start_time, 2)
            
            await self._broadcast_activity(
                "error", 
                f"Claude API call failed after {elapsed}s",
                {"error": error_msg[:200], "elapsed_seconds": elapsed}
            )
            
            logger.error(f"Claude API call failed: {error_msg}")
            
            # Check if it's a retryable error
            if is_retryable_error(e):
                await self._broadcast_activity("info", "Retrying API call with backoff...")
                logger.warning(f"Retryable error detected, will retry: {error_msg[:100]}")
            
            raise
    
    def load_knowledge_file(self, filename: str) -> str:
        """
        Load a sector knowledge file from /knowledge directory.
        """
        knowledge_path = Path("/app/knowledge") / filename
        
        if not knowledge_path.exists():
            logger.warning(f"Knowledge file not found: {filename}, using generic.md")
            knowledge_path = Path("/app/knowledge/generic.md")
        
        with open(knowledge_path, 'r') as f:
            return f.read()
