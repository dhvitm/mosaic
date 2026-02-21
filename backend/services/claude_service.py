from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
from dotenv import load_dotenv
from pathlib import Path
import logging

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)

class ClaudeService:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment")
    
    async def call_claude(self, system_message: str, user_prompt: str, session_id: str = "default") -> str:
        """
        Call Claude API with system message and user prompt.
        Uses prompt caching for sector knowledge files.
        """
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_message
            )
            
            # Use Anthropic Claude Sonnet 4.5
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            
            user_message = UserMessage(text=user_prompt)
            response = await chat.send_message(user_message)
            
            logger.info(f"Claude API call successful for session: {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Claude API call failed: {str(e)}")
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
