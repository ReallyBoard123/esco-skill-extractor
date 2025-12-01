"""Extraction endpoints"""

import time
from fastapi import APIRouter, HTTPException

from models.requests import ExtractRequest
from models.responses import ExtractResponse, ExtractBasicResponse

router = APIRouter()


@router.post("/extract-rich", response_model=ExtractResponse, tags=["Extraction"])
async def extract_rich(request: ExtractRequest, extractor):
    """Extract skills and occupations with full rich data"""
    try:
        start_time = time.time()
        
        # Extract with similarity scores
        skill_matches = extractor.extract_skills(
            request.text,
            threshold=request.skills_threshold,
            max_results=request.max_results
        )
        
        occupation_matches = extractor.extract_occupations(
            request.text,
            threshold=request.occupations_threshold,
            max_results=request.max_results
        )
        
        # Enrich with cross-referenced data
        rich_skills = []
        for skill_match in skill_matches:
            try:
                rich_skill = extractor.get_rich_skill_data(
                    skill_match['uri'],
                    similarity=skill_match['similarity']
                )
                rich_skills.append(rich_skill)
            except ValueError:
                continue
        
        rich_occupations = []
        for occupation_match in occupation_matches:
            try:
                rich_occupation = extractor.get_rich_occupation_data(
                    occupation_match['uri'],
                    similarity=occupation_match['similarity']
                )
                rich_occupations.append(rich_occupation)
            except ValueError:
                continue
        
        processing_time = time.time() - start_time
        
        return {
            "skills": rich_skills,
            "occupations": rich_occupations,
            "metadata": {
                "processedText": request.text,
                "totalSkillsFound": len(rich_skills),
                "totalOccupationsFound": len(rich_occupations),
                "processingTime": f"{processing_time:.2f}s",
                "thresholds": {
                    "skills": request.skills_threshold or extractor.skills_threshold,
                    "occupations": request.occupations_threshold or extractor.occupation_threshold
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting rich data: {str(e)}")


@router.post("/extract-basic", response_model=ExtractBasicResponse, tags=["Extraction"])
async def extract_basic(request: ExtractRequest, extractor):
    """Basic extraction for backward compatibility"""
    try:
        skill_matches = extractor.extract_skills(
            request.text,
            threshold=request.skills_threshold,
            max_results=request.max_results
        )
        
        occupation_matches = extractor.extract_occupations(
            request.text,
            threshold=request.occupations_threshold,
            max_results=request.max_results
        )
        
        return {
            "skills": [skill['name'] for skill in skill_matches],
            "occupations": [occ['name'] for occ in occupation_matches]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in basic extraction: {str(e)}")