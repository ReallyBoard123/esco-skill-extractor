"""Response models for ESCO API"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class SkillBasic(BaseModel):
    """Basic skill response"""
    name: str
    uri: str
    similarity: Optional[float] = None


class SkillRich(BaseModel):
    """Rich skill response with metadata"""
    name: str
    uri: str
    type: str
    reuseLevel: str
    description: str
    alternatives: List[str]
    categories: List[str]
    usedInOccupations: Dict[str, Any]
    similarity: Optional[float] = None


class OccupationBasic(BaseModel):
    """Basic occupation response"""
    name: str
    uri: str
    similarity: Optional[float] = None


class OccupationRich(BaseModel):
    """Rich occupation response with metadata"""
    name: str
    uri: str
    iscoGroup: str
    description: str
    alternatives: List[str]
    requiredSkills: Dict[str, Any]
    skillCategories: Dict[str, int]
    similarity: Optional[float] = None


class ExtractResponse(BaseModel):
    """Response for extraction endpoints"""
    skills: List[SkillRich]
    occupations: List[OccupationRich]
    metadata: Dict[str, Any]


class ExtractBasicResponse(BaseModel):
    """Basic extraction response for backward compatibility"""
    skills: List[str]
    occupations: List[str]


class SearchResponse(BaseModel):
    """Search results response"""
    results: List[Dict[str, Any]]
    total: int


class CategorySummaryResponse(BaseModel):
    """Category summary response"""
    categories: Dict[str, int]
    totalSkillsWithCategories: int
    totalSkills: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model: str
    data_version: str
    skills_count: int
    occupations_count: int


class InfoResponse(BaseModel):
    """API info response"""
    message: str
    version: str
    model: str
    data_version: str
    features: List[str]
    endpoints: Dict[str, str]