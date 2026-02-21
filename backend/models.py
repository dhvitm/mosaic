from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timezone
import uuid

class PipelineStep(BaseModel):
    step_number: int
    name: str
    status: Literal["pending", "in_progress", "completed", "error", "warning"]
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None

class ModelJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str
    status: Literal["pending", "processing", "completed", "failed"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_step: int = 0
    steps: List[PipelineStep] = []
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    excel_path: Optional[str] = None
    estimated_completion: Optional[datetime] = None

class ModelJobCreate(BaseModel):
    ticker: str

class CompanyMetadata(BaseModel):
    ticker: str
    full_name: str
    bse_code: str
    nse_code: str
    sector: str
    industry: str
    knowledge_file: str
    current_price: float
    market_cap: float
    shares_outstanding: float
    fiscal_year_end: str
    face_value: float

class SectorKnowledgeFile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    sector: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
