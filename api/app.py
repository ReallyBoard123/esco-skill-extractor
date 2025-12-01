"""Clean FastAPI application with all endpoints"""

import time
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from core.extractor import ESCOExtractor
from core.config import API_INFO
from models.requests import ExtractRequest

# Global extractor
_extractor = None


def create_app(
    model: str = "BAAI/bge-m3", 
    skills_threshold: float = 0.6,
    occupation_threshold: float = 0.55,
    device: str = None
) -> FastAPI:
    """Create simple FastAPI app"""
    
    global _extractor
    
    print(f"🚀 Initializing ESCO Extractor...")
    print(f"📊 Model: {model}")
    
    _extractor = ESCOExtractor(
        model=model,
        skills_threshold=skills_threshold,
        occupation_threshold=occupation_threshold,
        device=device
    )
    
    app = FastAPI(
        title=API_INFO["title"],
        description=API_INFO["description"],
        version=API_INFO["version"]
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        max_age=86400,
    )
    
    # Direct endpoint definitions
    @app.get("/", tags=["Info"])
    async def root():
        return {
            "message": API_INFO["title"],
            "version": API_INFO["version"],
            "model": model,
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
    
    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "healthy",
            "model": model,
            "data_version": "v1.2.0",
            "skills_count": len(_extractor._skill_data),
            "occupations_count": len(_extractor._occupation_data)
        }
    
    @app.get("/categories", tags=["Categories"])
    async def get_categories():
        return _extractor.get_category_summary()
    
    @app.post("/extract-rich", tags=["Extraction"])
    async def extract_rich(request: ExtractRequest):
        try:
            start_time = time.time()
            
            skill_matches = _extractor.extract_skills(
                request.text,
                threshold=request.skills_threshold,
                max_results=request.max_results
            )
            
            occupation_matches = _extractor.extract_occupations(
                request.text,
                threshold=request.occupations_threshold,
                max_results=request.max_results
            )
            
            # Enrich with cross-referenced data
            rich_skills = []
            for skill_match in skill_matches:
                try:
                    rich_skill = _extractor.get_rich_skill_data(
                        skill_match['uri'],
                        similarity=skill_match['similarity']
                    )
                    rich_skills.append(rich_skill)
                except ValueError:
                    continue
            
            rich_occupations = []
            for occupation_match in occupation_matches:
                try:
                    rich_occupation = _extractor.get_rich_occupation_data(
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
                        "skills": request.skills_threshold or _extractor.skills_threshold,
                        "occupations": request.occupations_threshold or _extractor.occupation_threshold
                    }
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extracting rich data: {str(e)}")
    
    @app.post("/extract-basic", tags=["Extraction"])
    async def extract_basic(request: ExtractRequest):
        try:
            skill_matches = _extractor.extract_skills(
                request.text,
                threshold=request.skills_threshold,
                max_results=request.max_results
            )
            
            occupation_matches = _extractor.extract_occupations(
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
    
    @app.post("/extract-pdf-skills", tags=["PDF Extraction"])
    async def extract_pdf_skills(
        pdf: UploadFile = File(...),
        skills_threshold: float = Form(0.6),
        occupations_threshold: float = Form(0.55),
        max_results: int = Form(10),
        rich_data: bool = Form(False)
    ):
        if not pdf.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        try:
            import fitz
            
            pdf_content = await pdf.read()
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            try:
                extracted_text = ""
                page_count = pdf_document.page_count  # Store before closing
                for page_num in range(page_count):
                    page = pdf_document[page_num]
                    extracted_text += page.get_text() + "\n"
                cleaned_text = extracted_text.strip()
            finally:
                pdf_document.close()
            
            if not cleaned_text:
                raise HTTPException(status_code=400, detail="PDF contains no extractable text")
            
            if rich_data:
                # Rich extraction
                skill_matches = _extractor.extract_skills(cleaned_text, threshold=skills_threshold, max_results=max_results)
                occupation_matches = _extractor.extract_occupations(cleaned_text, threshold=occupations_threshold, max_results=max_results)
                
                rich_skills = []
                for skill_match in skill_matches:
                    try:
                        rich_skill = _extractor.get_rich_skill_data(skill_match['uri'], similarity=skill_match['similarity'])
                        rich_skills.append(rich_skill)
                    except ValueError:
                        continue
                
                rich_occupations = []
                for occupation_match in occupation_matches:
                    try:
                        rich_occupation = _extractor.get_rich_occupation_data(occupation_match['uri'], similarity=occupation_match['similarity'])
                        rich_occupations.append(rich_occupation)
                    except ValueError:
                        continue
                
                return {
                    "skills": rich_skills,
                    "occupations": rich_occupations,
                    "metadata": {
                        "filename": pdf.filename,
                        "pages": page_count,
                        "text_length": len(cleaned_text),
                        "totalSkillsFound": len(rich_skills),
                        "totalOccupationsFound": len(rich_occupations),
                        "rich_data": True,
                        "extracted_text": cleaned_text
                    }
                }
            else:
                # Basic extraction
                skill_matches = _extractor.extract_skills(cleaned_text, threshold=skills_threshold, max_results=max_results)
                occupation_matches = _extractor.extract_occupations(cleaned_text, threshold=occupations_threshold, max_results=max_results)
                
                return {
                    "skills": [skill['name'] for skill in skill_matches],
                    "occupations": [occ['name'] for occ in occupation_matches],
                    "source_info": {
                        "filename": pdf.filename,
                        "pages": page_count,
                        "text_length": len(cleaned_text),
                        "extracted_text": cleaned_text
                    }
                }
        
        except ImportError:
            raise HTTPException(status_code=500, detail="PyMuPDF not installed")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")
    
    @app.get("/search/skills", tags=["Search"])
    async def search_skills(query: str, limit: int = 10):
        try:
            results = []
            query_lower = query.lower()
            
            for uri, skill_data in _extractor._skill_data.items():
                if (query_lower in skill_data['name'].lower() or
                    any(query_lower in alt.lower() for alt in skill_data['alternatives'])):
                    results.append({
                        'name': skill_data['name'],
                        'uri': uri,
                        'categories': _extractor._skill_categories.get(uri, []),
                        'type': skill_data['type']
                    })
                    
                    if len(results) >= limit:
                        break
            
            return {"results": results, "total": len(results)}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error searching skills: {str(e)}")
    
    @app.get("/search/occupations", tags=["Search"])
    async def search_occupations(query: str, limit: int = 10):
        try:
            results = []
            query_lower = query.lower()
            
            for uri, occ_data in _extractor._occupation_data.items():
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
    
    print(f"✅ Simple API initialized with {len(app.routes)} routes")
    return app