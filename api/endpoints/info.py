"""Info and utility endpoints"""

from fastapi import APIRouter, HTTPException

from models.responses import HealthResponse, InfoResponse, CategorySummaryResponse
from core.config import API_INFO

router = APIRouter()


@router.get("/", response_model=InfoResponse, tags=["Info"])
async def root(extractor=None):
    """API information"""
    return {
        "message": API_INFO["title"],
        "version": API_INFO["version"],
        "model": extractor.model_name,
        "data_version": "v1.2.0",
        "features": API_INFO["features"],
        "endpoints": {
            "extract_rich": "/extract-rich",
            "extract_basic": "/extract-basic",
            "extract_pdf": "/extract-pdf-skills",
            "search_skills": "/search/skills",
            "search_occupations": "/search/occupations",
            "health": "/health",
            "categories": "/categories"
        }
    }


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health(extractor=None):
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": extractor.model_name,
        "data_version": "v1.2.0",
        "skills_count": len(extractor._skill_data),
        "occupations_count": len(extractor._occupation_data)
    }


@router.get("/categories", response_model=CategorySummaryResponse, tags=["Categories"])
async def get_categories(extractor=None):
    """Get skill categories summary"""
    try:
        return extractor.get_category_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving categories: {str(e)}")


@router.get("/skill/{skill_uri:path}", tags=["Details"])
async def get_skill_details(skill_uri: str, extractor=None):
    """Get comprehensive details for a specific skill"""
    try:
        # Ensure URI is properly formatted
        if not skill_uri.startswith("http"):
            skill_uri = f"http://data.europa.eu/esco/skill/{skill_uri}"
        
        rich_skill = extractor.get_rich_skill_data(skill_uri)
        return rich_skill
        
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_uri}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving skill: {str(e)}")


@router.get("/occupation/{occupation_uri:path}", tags=["Details"])
async def get_occupation_details(occupation_uri: str, extractor=None):
    """Get comprehensive details for a specific occupation"""
    try:
        # Ensure URI is properly formatted
        if not occupation_uri.startswith("http"):
            occupation_uri = f"http://data.europa.eu/esco/occupation/{occupation_uri}"
        
        rich_occupation = extractor.get_rich_occupation_data(occupation_uri)
        return rich_occupation
        
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Occupation not found: {occupation_uri}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving occupation: {str(e)}")