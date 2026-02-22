import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime, timezone
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Map of job_id to set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, job_id: str):
        """Accept and register a WebSocket connection for a job"""
        await websocket.accept()
        
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        
        self.active_connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job {job_id}. Total connections: {len(self.active_connections[job_id])}")
    
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Remove a WebSocket connection"""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            
            # Clean up empty job entries
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
            
            logger.info(f"WebSocket disconnected for job {job_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {str(e)}")
    
    async def broadcast_to_job(self, job_id: str, message: dict):
        """Broadcast a message to all WebSocket connections watching a specific job"""
        if job_id not in self.active_connections:
            return
        
        dead_connections = set()
        
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {str(e)}")
                dead_connections.add(connection)
        
        # Remove dead connections
        for connection in dead_connections:
            self.disconnect(connection, job_id)
    
    async def send_step_update(self, job_id: str, step_number: int, status: str, message: str = "", data: dict = None):
        """Send a step update to all connections watching a job"""
        update = {
            'type': 'step_update',
            'job_id': job_id,
            'step_number': step_number,
            'status': status,
            'message': message,
            'data': data or {}
        }
        
        await self.broadcast_to_job(job_id, update)
    
    async def send_job_status(self, job_id: str, status: str, current_step: int = 0):
        """Send job status update"""
        update = {
            'type': 'job_status',
            'job_id': job_id,
            'status': status,
            'current_step': current_step
        }
        
        await self.broadcast_to_job(job_id, update)
    
    async def send_completion(self, job_id: str, result: dict):
        """Send job completion notification"""
        update = {
            'type': 'job_complete',
            'job_id': job_id,
            'result': result
        }
        
        await self.broadcast_to_job(job_id, update)
    
    async def send_error(self, job_id: str, error: str):
        """Send error notification"""
        update = {
            'type': 'error',
            'job_id': job_id,
            'error': error
        }
        
        await self.broadcast_to_job(job_id, update)
    
    async def send_activity(self, job_id: str, activity_type: str, message: str, details: dict = None):
        """Send real-time activity log updates (API calls, LLM thinking, etc.)"""
        update = {
            'type': 'activity_log',
            'job_id': job_id,
            'activity_type': activity_type,  # 'api_call', 'llm_thinking', 'data_processing', 'info'
            'message': message,
            'details': details or {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        await self.broadcast_to_job(job_id, update)

# Global WebSocket manager instance
ws_manager = ConnectionManager()
