from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from datetime import datetime, timezone
import os
import logging
from pathlib import Path

from backend.models import ModelJob, ModelJobCreate
from backend.services.pipeline_manager import PipelineManager
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

@router.post("/", response_model=ModelJob)
async def create_model_job(job_input: ModelJobCreate, background_tasks: BackgroundTasks):
    """
    Create a new model generation job and start the pipeline
    """
    try:
        # Create job
        job = ModelJob(
            ticker=job_input.ticker.upper(),
            status="pending",
            steps=[]
        )
        
        # Save to database
        job_dict = job.model_dump()
        job_dict['created_at'] = job_dict['created_at'].isoformat()
        job_dict['updated_at'] = job_dict['updated_at'].isoformat()
        
        await db.model_jobs.insert_one(job_dict)
        
        # Start pipeline in background
        pipeline = PipelineManager(db)
        background_tasks.add_task(pipeline.run_pipeline, job.id, job.ticker)
        
        logger.info(f"Created job {job.id} for ticker {job.ticker}")
        return job
        
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress/{job_id}", response_model=ModelJob)
async def get_job_progress(job_id: str):
    """
    Get the current progress of a job
    """
    try:
        job = await db.model_jobs.find_one({"id": job_id}, {"_id": 0})
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Convert ISO strings back to datetime
        if isinstance(job.get('created_at'), str):
            job['created_at'] = datetime.fromisoformat(job['created_at'])
        if isinstance(job.get('updated_at'), str):
            job['updated_at'] = datetime.fromisoformat(job['updated_at'])
        if isinstance(job.get('estimated_completion'), str):
            job['estimated_completion'] = datetime.fromisoformat(job['estimated_completion'])
        
        # Convert step timestamps
        if job.get('steps'):
            for step in job['steps']:
                if isinstance(step.get('started_at'), str):
                    step['started_at'] = datetime.fromisoformat(step['started_at'])
                if isinstance(step.get('completed_at'), str):
                    step['completed_at'] = datetime.fromisoformat(step['completed_at'])
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{job_id}")
async def get_job_result(job_id: str):
    """
    Get the final result of a completed job
    """
    try:
        job = await db.model_jobs.find_one({"id": job_id}, {"_id": 0})
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] != 'completed':
            raise HTTPException(status_code=400, detail=f"Job status is {job['status']}, not completed")
        
        return {
            "job_id": job_id,
            "ticker": job['ticker'],
            "result": job.get('result', {}),
            "excel_path": job.get('excel_path'),
            "created_at": job.get('created_at'),
            "completed_at": job.get('updated_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job result: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{job_id}")
async def download_excel(job_id: str):
    """
    Download the Excel model for a completed job
    """
    from fastapi.responses import FileResponse
    
    try:
        job = await db.model_jobs.find_one({"id": job_id}, {"_id": 0})
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        excel_path = job.get('excel_path')
        if not excel_path or not os.path.exists(excel_path):
            raise HTTPException(status_code=404, detail="Excel file not found")
        
        filename = os.path.basename(excel_path)
        return FileResponse(
            path=excel_path,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading Excel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=List[ModelJob])
async def list_jobs(limit: int = 20):
    """
    List recent model generation jobs
    """
    try:
        jobs = await db.model_jobs.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        
        # Convert timestamps
        for job in jobs:
            if isinstance(job.get('created_at'), str):
                job['created_at'] = datetime.fromisoformat(job['created_at'])
            if isinstance(job.get('updated_at'), str):
                job['updated_at'] = datetime.fromisoformat(job['updated_at'])
        
        return jobs
        
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
