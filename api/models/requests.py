"""Request models for ESCO API"""

from typing import Optional
from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    """Request for skill/occupation extraction"""
    text: str = Field(..., description="Text to analyze")
    skills_threshold: Optional[float] = Field(None, ge=0, le=1, description="Similarity threshold for skills")
    occupations_threshold: Optional[float] = Field(None, ge=0, le=1, description="Similarity threshold for occupations")
    max_results: Optional[int] = Field(10, ge=1, le=100, description="Maximum results to return")


class SearchRequest(BaseModel):
    """Request for search"""
    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Maximum results")


class PDFExtractRequest(BaseModel):
    """Request for PDF extraction (form data)"""
    skills_threshold: float = Field(0.6, ge=0, le=1)
    occupations_threshold: float = Field(0.55, ge=0, le=1) 
    max_results: int = Field(10, ge=1, le=50)
    rich_data: bool = Field(False, description="Return rich data or basic format")
