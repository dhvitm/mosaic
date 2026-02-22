from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from typing import List, Optional
from pydantic import BaseModel
import os
from pathlib import Path
import logging
import sys

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from models import SectorKnowledgeFile
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

KNOWLEDGE_DIR = Path("/app/knowledge")


class FileUpdateRequest(BaseModel):
    content: str


class FileCreateRequest(BaseModel):
    filename: str
    content: str

@router.get("/knowledge-files")
async def list_knowledge_files():
    """
    List all sector knowledge files
    """
    try:
        files = []
        for file_path in KNOWLEDGE_DIR.glob("*.md"):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract sector from first line
            first_line = content.split('\n')[0] if content else ''
            sector = first_line.replace('# SECTOR:', '').strip() if 'SECTOR:' in first_line else file_path.stem
            
            files.append({
                "filename": file_path.name,
                "sector": sector,
                "size": len(content),
                "preview": content[:200] + "..."
            })
        
        return {"files": files, "total": len(files)}
        
    except Exception as e:
        logger.error(f"Error listing knowledge files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge-files/{filename}")
async def get_knowledge_file(filename: str):
    """
    Get content of a specific knowledge file
    """
    try:
        file_path = KNOWLEDGE_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Knowledge file not found")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        return {"filename": filename, "content": content}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading knowledge file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/knowledge-files/{filename}")
async def update_knowledge_file(filename: str, request: FileUpdateRequest):
    """
    Update a knowledge file
    """
    try:
        file_path = KNOWLEDGE_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Knowledge file not found")
        
        with open(file_path, 'w') as f:
            f.write(request.content)
        
        logger.info(f"Updated knowledge file: {filename}")
        return {"message": "Knowledge file updated successfully", "filename": filename}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating knowledge file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge-files")
async def create_knowledge_file(request: FileCreateRequest):
    """
    Create a new knowledge file
    """
    try:
        filename = request.filename
        if not filename.endswith('.md'):
            filename += '.md'
        
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in "._-").lower()
        
        file_path = KNOWLEDGE_DIR / filename
        
        if file_path.exists():
            raise HTTPException(status_code=400, detail="Knowledge file already exists")
        
        with open(file_path, 'w') as f:
            f.write(request.content)
        
        logger.info(f"Created knowledge file: {filename}")
        return {"message": "Knowledge file created successfully", "filename": filename}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating knowledge file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/knowledge-files/{filename}")
async def delete_knowledge_file(filename: str):
    """
    Delete a knowledge file (except banks.md and generic.md)
    """
    try:
        if filename in ['banks.md', 'generic.md']:
            raise HTTPException(status_code=400, detail="Cannot delete default knowledge files")
        
        file_path = KNOWLEDGE_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Knowledge file not found")
        
        os.remove(file_path)
        
        logger.info(f"Deleted knowledge file: {filename}")
        return {"message": "Knowledge file deleted successfully", "filename": filename}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-gaps")
async def get_knowledge_gaps():
    """
    Get all flagged knowledge gaps for human review.
    These are gaps identified by the Mosaic agent when it lacks
    sufficient sector context to make assumptions.
    """
    try:
        gaps_file = KNOWLEDGE_DIR / "knowledge_gaps.json"
        
        if not gaps_file.exists():
            return {"gaps": [], "total": 0, "by_sector": {}}
        
        gaps = json.loads(gaps_file.read_text())
        
        # Group by sector
        by_sector = {}
        for gap in gaps:
            sector = gap.get("sector", "unknown")
            if sector not in by_sector:
                by_sector[sector] = []
            by_sector[sector].append(gap)
        
        return {
            "gaps": gaps,
            "total": len(gaps),
            "by_sector": by_sector
        }
    except Exception as e:
        logger.error(f"Error reading knowledge gaps: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge-gaps/{index}")
async def resolve_knowledge_gap(index: int):
    """
    Mark a knowledge gap as resolved (removes it from the list)
    """
    try:
        gaps_file = KNOWLEDGE_DIR / "knowledge_gaps.json"
        
        if not gaps_file.exists():
            raise HTTPException(status_code=404, detail="No knowledge gaps file found")
        
        gaps = json.loads(gaps_file.read_text())
        
        if index < 0 or index >= len(gaps):
            raise HTTPException(status_code=404, detail="Gap index out of range")
        
        removed = gaps.pop(index)
        gaps_file.write_text(json.dumps(gaps, indent=2))
        
        return {"message": "Knowledge gap resolved", "removed": removed}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving knowledge gap: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
