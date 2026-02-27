from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import List
from datetime import datetime, timezone
import os
import logging
from pathlib import Path
import sys

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from models import ModelJob, ModelJobCreate
from services.pipeline_manager import PipelineManager
from services.scraper_service import ScraperService
from services.websocket_manager import ws_manager
from services.cache_service import CacheService
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
    Create a new model generation job and start the pipeline.
    Prevents duplicate jobs for the same ticker.
    """
    try:
        ticker = job_input.ticker.upper()
        
        # Check if there's already a processing job for this ticker
        existing_job = await db.model_jobs.find_one(
            {"ticker": ticker, "status": "processing"},
            {"_id": 0}
        )
        
        if existing_job:
            logger.info(f"Found existing processing job for {ticker}: {existing_job['id']}")
            # Convert timestamps
            if isinstance(existing_job.get('created_at'), str):
                existing_job['created_at'] = datetime.fromisoformat(existing_job['created_at'])
            if isinstance(existing_job.get('updated_at'), str):
                existing_job['updated_at'] = datetime.fromisoformat(existing_job['updated_at'])
            return existing_job
        
        # Create job
        job = ModelJob(
            ticker=ticker,
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
        
        logger.info(f"Created job {job.id} for ticker {ticker}")
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

@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates
    """
    await ws_manager.connect(websocket, job_id)
    
    try:
        # Send initial job status
        job = await db.model_jobs.find_one({"id": job_id}, {"_id": 0})
        if job:
            await websocket.send_json({
                'type': 'connected',
                'job_id': job_id,
                'status': job.get('status'),
                'current_step': job.get('current_step', 0)
            })
        
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Echo back for keepalive
            await websocket.send_json({'type': 'pong'})
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {str(e)}")
        ws_manager.disconnect(websocket, job_id)

@router.get("/validate-ticker/{ticker}")
async def validate_ticker(ticker: str):
    """
    Validate if a ticker exists on Screener.in
    """
    try:
        scraper = ScraperService()
        is_valid = await scraper.validate_ticker(ticker.upper())
        await scraper.close()
        
        return {
            "ticker": ticker.upper(),
            "valid": is_valid,
            "message": "Ticker found" if is_valid else "Ticker not found on Screener.in"
        }
        
    except Exception as e:
        logger.error(f"Error validating ticker {ticker}: {str(e)}")
        # Return as potentially valid if validation fails
        return {
            "ticker": ticker.upper(),
            "valid": True,
            "message": "Unable to validate - proceeding"
        }

@router.get("/cache-status/{ticker}")
async def get_cache_status(ticker: str):
    """
    Get cached data status for a ticker
    """
    try:
        status = CacheService.get_cache_status(ticker.upper())
        return status
    except Exception as e:
        logger.error(f"Error getting cache status for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cached-tickers")
async def list_cached_tickers():
    """
    List all tickers with cached data
    """
    try:
        tickers = CacheService.list_all_cached_tickers()
        return {"tickers": tickers, "total": len(tickers)}
    except Exception as e:
        logger.error(f"Error listing cached tickers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/{ticker}")
async def get_ticker_cache(ticker: str):
    """
    Get detailed cache data for a specific ticker
    """
    try:
        ticker = ticker.upper()
        status = CacheService.get_cache_status(ticker)
        
        if not status['has_cache'] or not status['cached_steps']:
            raise HTTPException(status_code=404, detail=f"No cache found for {ticker}")
        
        # Load actual data for each cached step
        cache_data = {
            "ticker": ticker,
            "cached_steps": [],
            "total_steps": len(status['cached_steps'])
        }
        
        step_names = {
            1: "Company Identification",
            2: "Annual Financial Data",
            3: "Operational Metrics",
            4: "Management Commentary",
            5: "Forecast Assumptions",
            6: "Excel Model",
            7: "Valuation",
            8: "Investment Thesis"
        }
        
        for step_info in status['cached_steps']:
            step_num = step_info['step']
            step_data = CacheService.load_step_data(ticker, step_num)
            
            cache_data['cached_steps'].append({
                "step_number": step_num,
                "step_name": step_names.get(step_num, f"Step {step_num}"),
                "cached_at": step_info['cached_at'],
                "size_kb": step_info['size_kb'],
                "data": step_data
            })
        
        return cache_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cache/{ticker}")
async def clear_ticker_cache(ticker: str):
    """
    Clear all cached data for a specific ticker
    """
    try:
        ticker = ticker.upper()
        CacheService.clear_ticker_cache(ticker)
        return {"message": f"Cache cleared for {ticker}", "ticker": ticker}
    except Exception as e:
        logger.error(f"Error clearing cache for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry/{job_id}")
async def retry_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Retry a failed job - will use cached data from previous successful steps
    """
    try:
        # Get the original job
        job = await db.model_jobs.find_one({"id": job_id}, {"_id": 0})
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] == 'processing':
            raise HTTPException(status_code=400, detail="Job is still processing")
        
        ticker = job['ticker']
        
        # Create a new job for retry
        new_job = ModelJob(
            ticker=ticker,
            status="pending",
            steps=[]
        )
        
        # Save to database
        job_dict = new_job.model_dump()
        job_dict['created_at'] = job_dict['created_at'].isoformat()
        job_dict['updated_at'] = job_dict['updated_at'].isoformat()
        
        await db.model_jobs.insert_one(job_dict)
        
        # Start pipeline (will use cached data automatically)
        pipeline = PipelineManager(db)
        background_tasks.add_task(pipeline.run_pipeline, new_job.id, ticker)
        
        logger.info(f"Created retry job {new_job.id} for ticker {ticker}")
        
        # Return info about what will be cached
        cache_status = CacheService.get_cache_status(ticker)
        
        return {
            "message": f"Retry job created for {ticker}",
            "new_job_id": new_job.id,
            "original_job_id": job_id,
            "cached_steps": cache_status.get('cached_steps', []),
            "will_skip_steps": len(cache_status.get('cached_steps', []))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/abort/{job_id}")
async def abort_job(job_id: str):
    """
    Abort a running job by marking it as failed.
    Note: This doesn't stop the background task, but prevents further steps.
    """
    try:
        # Get the job
        job = await db.model_jobs.find_one({"id": job_id}, {"_id": 0})
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] != 'processing':
            raise HTTPException(status_code=400, detail=f"Job is not processing (status: {job['status']})")
        
        # Mark job as aborted/failed
        await db.model_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "failed",
                "error": "Job aborted by user",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Broadcast abort via WebSocket
        await ws_manager.send_error(job_id, "Job aborted by user")
        
        logger.info(f"Job {job_id} aborted by user")
        
        return {
            "message": f"Job {job_id} aborted",
            "job_id": job_id,
            "ticker": job['ticker'],
            "previous_status": "processing",
            "new_status": "failed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error aborting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# LLM Logs Endpoints
# ============================================================================

from services.llm_logger import get_logs_for_ticker, get_log_for_job, list_all_logs

@router.get("/logs/")
async def get_all_llm_logs():
    """Get list of all LLM log files (metadata only)."""
    try:
        logs = list_all_logs()
        return {
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        logger.error(f"Error fetching LLM logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/ticker/{ticker}")
async def get_llm_logs_for_ticker(ticker: str):
    """Get all LLM logs for a specific ticker."""
    try:
        ticker = ticker.upper()
        logs = get_logs_for_ticker(ticker)
        
        if not logs:
            raise HTTPException(status_code=404, detail=f"No logs found for ticker {ticker}")
        
        return {
            "ticker": ticker,
            "log_count": len(logs),
            "logs": logs
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching LLM logs for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/job/{job_id}")
async def get_llm_log_for_job(job_id: str):
    """Get LLM log for a specific job."""
    try:
        log = get_log_for_job(job_id)
        
        if not log:
            raise HTTPException(status_code=404, detail=f"No log found for job {job_id}")
        
        return log
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching LLM log for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
