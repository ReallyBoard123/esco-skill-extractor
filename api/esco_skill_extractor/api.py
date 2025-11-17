"""FastAPI application for ESCO Skill Extractor"""

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import TextsInput, HealthResponse, SkillsResponse, OccupationsResponse


def create_app(extractor, model_name: str) -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="ESCO Skill Extractor API",
        description="Extract ESCO skills and ISCO occupations from text using transformer embeddings",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["Info"])
    async def root():
        """Root endpoint with API information"""
        return {
            "message": "ESCO Skill Extractor API",
            "version": "1.0.0",
            "model": model_name,
            "docs": "/docs",
            "health": "/health"
        }

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health():
        """Health check endpoint"""
        return HealthResponse(status="healthy", model=model_name)

    @app.post("/extract-skills", response_model=SkillsResponse, tags=["Extraction"])
    async def extract_skills(input_data: TextsInput):
        """Extract ESCO skills from input texts"""
        try:
            skills = extractor.get_skills(input_data.texts, input_data.threshold)
            return SkillsResponse(skills=skills)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extracting skills: {str(e)}")

    @app.post("/extract-occupations", response_model=OccupationsResponse, tags=["Extraction"])
    async def extract_occupations(input_data: TextsInput):
        """Extract ISCO occupations from input texts"""
        try:
            occupations = extractor.get_occupations(input_data.texts, input_data.threshold)
            return OccupationsResponse(occupations=occupations)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extracting occupations: {str(e)}")


    return app