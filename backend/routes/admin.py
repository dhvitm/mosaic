from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import os
from pathlib import Path
import logging

from backend.models import SectorKnowledgeFile
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

KNOWLEDGE_DIR = Path("/app/knowledge")

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
async def update_knowledge_file(filename: str, content: str):
    """
    Update a knowledge file
    """
    try:
        file_path = KNOWLEDGE_DIR / filename
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Updated knowledge file: {filename}")
        return {"message": "Knowledge file updated successfully", "filename": filename}
        
    except Exception as e:
        logger.error(f"Error updating knowledge file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge-files")
async def create_knowledge_file(filename: str, content: str):
    """
    Create a new knowledge file
    """
    try:
        if not filename.endswith('.md'):
            filename += '.md'
        
        file_path = KNOWLEDGE_DIR / filename
        
        if file_path.exists():
            raise HTTPException(status_code=400, detail="Knowledge file already exists")
        
        with open(file_path, 'w') as f:
            f.write(content)
        
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
