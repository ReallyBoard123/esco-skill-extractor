"""Clean FastAPI application with all endpoints"""

import time
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from core.extractor import ESCOExtractor
from core.intelligent_analyzer import IntelligentCVAnalyzer
from core.config import API_INFO
from models.requests import ExtractRequest

# Global extractors
_extractor = None
_intelligent_analyzer = None


def create_app(
    model: str = "BAAI/bge-m3", 
    skills_threshold: float = 0.6,
    occupation_threshold: float = 0.55,
    device: str = None
) -> FastAPI:
    """Create simple FastAPI app"""
    
    global _extractor, _intelligent_analyzer
    
    print(f"🚀 Initializing ESCO Extractor...")
    print(f"📊 Model: {model}")
    
    _extractor = ESCOExtractor(
        model=model,
        skills_threshold=skills_threshold,
        occupation_threshold=occupation_threshold,
        device=device
    )
    
    print(f"🧠 Initializing Intelligent CV Analyzer...")
    _intelligent_analyzer = IntelligentCVAnalyzer()
    
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
    
    # Legacy extraction/search endpoints removed (use intelligent endpoints instead)
    
    # Legacy extraction/search endpoints removed (use intelligent endpoints instead)
    
    @app.post("/analyze-cv-intelligent", tags=["Intelligent Analysis"])
    async def analyze_cv_intelligent(
        pdf: UploadFile = File(...),
        detailed_analysis: bool = Form(True),
        skills_threshold: float = Form(0.6),
        occupations_threshold: float = Form(0.55),
        max_results: int = Form(30)
    ):
        """Intelligent CV analysis using BGE-M3 + Gemma3 4B hybrid system with prefilter"""
        
        if not pdf.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        try:
            pdf_content = await pdf.read()
            analysis_result = _intelligent_analyzer.analyze_pdf_cv_prefiltered(
                pdf_content,
                skills_threshold=skills_threshold,
                occupations_threshold=occupations_threshold,
                max_results=max_results
            )
            
            analysis_result["file_info"] = {
                "filename": pdf.filename,
                "size_bytes": len(pdf_content),
                "analysis_type": "intelligent_hybrid_prefilter"
            }
            
            return analysis_result
            
        except ImportError:
            raise HTTPException(status_code=500, detail="PyMuPDF not installed for PDF processing")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Intelligent analysis failed: {str(e)}")
    
    @app.post("/analyze-text-intelligent", tags=["Intelligent Analysis"]) 
    async def analyze_text_intelligent(request: ExtractRequest):
        """Intelligent text analysis using BGE-M3 + Gemma3 4B hybrid system"""
        
        try:
            # Perform intelligent analysis
            analysis_result = _intelligent_analyzer.analyze_text_cv_prefiltered(
                request.text,
                metadata={"source": "text_prefiltered_request", "text_length": len(request.text)},
                skills_threshold=request.skills_threshold,
                occupations_threshold=request.occupations_threshold,
                max_results=request.max_results
            )
            
            return analysis_result
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Intelligent text analysis failed: {str(e)}")

    @app.post("/analyze-text-intelligent-prefilter", tags=["Intelligent Analysis"])
    async def analyze_text_intelligent_prefilter(request: ExtractRequest):
        """Gemma-first filtering followed by intelligent analysis"""
        try:
            analysis_result = _intelligent_analyzer.analyze_text_cv_prefiltered(request.text)
            return analysis_result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prefiltered intelligent analysis failed: {str(e)}")
    
    print(f"✅ Intelligent API initialized with {len(app.routes)} routes")
    return app
