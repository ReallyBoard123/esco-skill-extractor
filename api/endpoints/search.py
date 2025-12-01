"""Search endpoints"""

from fastapi import APIRouter, HTTPException

from models.requests import SearchRequest
from models.responses import SearchResponse

router = APIRouter()


@router.get("/search/skills", response_model=SearchResponse, tags=["Search"])
async def search_skills(query: str, limit: int = 10, extractor=None):
    """Search skills by name/description"""
    try:
        results = []
        query_lower = query.lower()
        
        for uri, skill_data in extractor._skill_data.items():
            if (query_lower in skill_data['name'].lower() or
                any(query_lower in alt.lower() for alt in skill_data['alternatives'])):
                results.append({
                    'name': skill_data['name'],
                    'uri': uri,
                    'categories': extractor._skill_categories.get(uri, []),
                    'type': skill_data['type']
                })
                
                if len(results) >= limit:
                    break
        
        return {"results": results, "total": len(results)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching skills: {str(e)}")


@router.get("/search/occupations", response_model=SearchResponse, tags=["Search"])
async def search_occupations(query: str, limit: int = 10, extractor=None):
    """Search occupations by name/description"""
    try:
        results = []
        query_lower = query.lower()
        
        for uri, occ_data in extractor._occupation_data.items():
            if (query_lower in occ_data['name'].lower() or
                any(query_lower in alt.lower() for alt in occ_data['alternatives'])):
                results.append({
                    'name': occ_data['name'],
                    'uri': uri,
                    'iscoGroup': occ_data['iscoGroup'],
                    'description': occ_data['description'][:200] + '...' if len(occ_data['description']) > 200 else occ_data['description']
                })
                
                if len(results) >= limit:
                    break
        
        return {"results": results, "total": len(results)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching occupations: {str(e)}")