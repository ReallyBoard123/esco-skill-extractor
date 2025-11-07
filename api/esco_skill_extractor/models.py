"""Pydantic models for API request/response validation"""

from typing import List
from pydantic import BaseModel, Field


class TextsInput(BaseModel):
    """Input model for text processing endpoints"""
    texts: List[str] = Field(
        ..., 
        description="List of text strings to analyze",
        min_items=1,
        max_items=100,
        example=["I am a software engineer with Python experience"]
    )


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(description="API health status")
    model: str = Field(description="Currently loaded model name")


class SkillsResponse(BaseModel):
    """Skills extraction response model"""
    skills: List[List[str]] = Field(
        description="List of ESCO skill URLs for each input text"
    )


class OccupationsResponse(BaseModel):
    """Occupations extraction response model"""
    occupations: List[List[str]] = Field(
        description="List of ESCO occupation URLs for each input text"
    )