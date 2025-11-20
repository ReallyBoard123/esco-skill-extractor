"""FastAPI application for ESCO Skill Extractor"""

from typing import List

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
        allow_credentials=False,  # Set to False for zrok compatibility
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language", 
            "Content-Language",
            "Content-Type",
            "Authorization",
            "Origin",
            "X-Requested-With",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers",
            "skip_zrok_interstitial",  # Allow zrok bypass header
        ],
        expose_headers=[
            "Content-Type",
            "Content-Length", 
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
        ],
        max_age=86400,  # Cache preflight for 24 hours
    )

    # Add explicit OPTIONS handler for CORS preflight
    @app.options("/{path:path}")
    async def handle_options(request: Request, path: str):
        """Handle CORS preflight requests for all endpoints"""
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Origin, X-Requested-With, Accept, skip_zrok_interstitial",
                "Access-Control-Max-Age": "86400",
            }
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

    @app.post("/extract-pdf-skills", tags=["Extraction"])
    async def extract_pdf_skills(
        pdf: UploadFile = File(...), 
        skill_threshold: float = Form(0.6),
        occupation_threshold: float = Form(0.55)
    ):
        """Extract skills and occupations directly from uploaded PDF file"""
        print(f"DEBUG: Received thresholds - skills: {skill_threshold}, occupations: {occupation_threshold}")
        
        if not pdf.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        try:
            import fitz  # PyMuPDF
            
            # Read PDF content and extract text
            pdf_content = await pdf.read()
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            try:
                page_count = pdf_document.page_count
                extracted_text = ""
                
                for page_num in range(page_count):
                    page = pdf_document[page_num]
                    text = page.get_text()
                    extracted_text += text + "\n"
                
                cleaned_text = extracted_text.strip()
                
            finally:
                pdf_document.close()
            
            if not cleaned_text:
                raise HTTPException(status_code=400, detail="PDF contains no extractable text")
            
            # Extract skills and occupations from the text
            print(f"DEBUG: Extracting from text length: {len(cleaned_text)}")
            skills = extractor.get_skills([cleaned_text], skill_threshold)
            print(f"DEBUG: Skills extraction completed: {len(skills[0])} skills")
            occupations = extractor.get_occupations([cleaned_text], occupation_threshold)
            print(f"DEBUG: Occupations extraction completed: {len(occupations[0])} occupations")
            
            return {
                "skills": skills[0],  # Flatten the nested array
                "occupations": occupations[0],  # Flatten the nested array
                "source_info": {
                    "filename": pdf.filename,
                    "pages": page_count,
                    "text_length": len(cleaned_text)
                }
            }
            
        except ImportError:
            raise HTTPException(status_code=500, detail="PyMuPDF not installed. Run: pip install PyMuPDF")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

    def _extract_skill_name(description: str) -> str:
        """Extract the best skill name from ESCO description"""
        # Handle programming languages and technologies first
        if any(tech in description.upper() for tech in ['CSS', 'HTML', 'JAVASCRIPT', 'PYTHON', 'JAVA', 'SQL', 'R ']):
            # For tech skills, look for the technology name
            words = description.split()
            for i, word in enumerate(words):
                if word.upper() in ['CSS', 'HTML', 'JAVASCRIPT', 'PYTHON', 'JAVA', 'SQL']:
                    return word
                if word == 'R' and (i == 0 or words[i-1] not in ['for', 'and', 'or']):
                    return 'R'
        
        # Split description into parts: synonyms + detailed description
        parts = description.split('.')
        if len(parts) > 1:
            # Use the part before the first period as synonym list
            synonyms_part = parts[0].strip()
        else:
            # Look for capital letter indicating start of sentence
            words = description.split()
            synonyms_end = 0
            for i, word in enumerate(words):
                if word[0].isupper() and i > 0 and not any(char.isupper() for char in word[1:]):
                    synonyms_end = i
                    break
            if synonyms_end > 0:
                synonyms_part = ' '.join(words[:synonyms_end])
            else:
                synonyms_part = description
        
        # From synonyms, pick the best meaningful phrase
        words = synonyms_part.split()
        
        # For skills, prefer 1-3 word combinations that make sense
        if len(words) >= 2:
            # Check if first two words form a good skill name
            two_word = ' '.join(words[:2])
            # Prefer two-word skills for actions + objects
            if any(action in words[0].lower() for action in ['prepare', 'manage', 'develop', 'implement', 'create', 'design', 'apply', 'use', 'perform']):
                if len(words) >= 2 and words[1].lower() not in ['the', 'a', 'an', 'of', 'for', 'and', 'or', 'in', 'to']:
                    return two_word
            # Single word for simple skills
            return words[0]
        else:
            return words[0] if words else description
    
    def _extract_occupation_name(description: str) -> str:
        """Extract the best occupation name from ESCO description"""
        # Split description into parts
        parts = description.split('.')
        if len(parts) > 1:
            synonyms_part = parts[0].strip()
        else:
            # Look for capital letter indicating start of sentence
            words = description.split()
            synonyms_end = 0
            for i, word in enumerate(words):
                if word[0].isupper() and i > 0:
                    synonyms_end = i
                    break
            if synonyms_end > 0:
                synonyms_part = ' '.join(words[:synonyms_end])
            else:
                synonyms_part = description
        
        # For occupations, prefer the first 1-2 words as they're usually the job title
        words = synonyms_part.split()
        if len(words) >= 2:
            # Try to find the core job title (usually first 1-2 words)
            candidate = ' '.join(words[:2])
            # Avoid repetitive patterns like "event manager event"
            first_word = words[0].lower()
            if len(words) > 2 and words[1].lower() == first_word:
                return words[0]  # Just return first word if repetitive
            return candidate
        elif len(words) == 1:
            return words[0]
        else:
            return description

    @app.post("/decode-esco", tags=["Extraction"])
    async def decode_esco(request: dict):
        """Decode ESCO URLs to human-readable names"""
        try:
            import pandas as pd
            import os
            
            skills = request.get("skills", [])
            occupations = request.get("occupations", [])
            
            # Load improved CSV files (fallback to old format if v2 doesn't exist)
            skills_csv_path = os.path.join(extractor._dir, "data", "skills_v2.csv")
            if not os.path.exists(skills_csv_path):
                skills_csv_path = os.path.join(extractor._dir, "data", "skills.csv")
            
            occupations_csv_path = os.path.join(extractor._dir, "data", "occupations_v2.csv")
            if not os.path.exists(occupations_csv_path):
                occupations_csv_path = os.path.join(extractor._dir, "data", "occupations.csv")
            
            decoded_skills = []
            decoded_occupations = []
            
            # Decode skills
            if skills and os.path.exists(skills_csv_path):
                skills_df = pd.read_csv(skills_csv_path)
                
                # Check if we're using the new schema (has preferred_name column)
                using_new_schema = 'preferred_name' in skills_df.columns
                
                for skill_url in skills:
                    # Extract ID from URL or use as-is if it's just an ID
                    skill_id = skill_url.split('/')[-1] if '/' in skill_url else skill_url
                    match = skills_df[skills_df.iloc[:, 0].str.contains(skill_id, na=False)]
                    if not match.empty:
                        if using_new_schema:
                            # Use clean preferred_name from new schema
                            preferred_name = match.iloc[0]['preferred_name']
                            main_name = preferred_name
                        else:
                            # Fallback to old parsing method
                            description = match.iloc[0, 1].strip().strip('"')
                            main_name = self._extract_skill_name(description)
                        
                        decoded_skills.append({
                            "id": skill_url,
                            "description": main_name
                        })
                    else:
                        decoded_skills.append({
                            "id": skill_url,
                            "description": skill_id
                        })
            
            # Decode occupations
            if occupations and os.path.exists(occupations_csv_path):
                occupations_df = pd.read_csv(occupations_csv_path)
                
                # Check if we're using the new schema (has preferred_name column)
                using_new_schema = 'preferred_name' in occupations_df.columns
                
                for occ_url in occupations:
                    # Extract ID from URL or use as-is if it's just an ID
                    occ_id = occ_url.split('/')[-1] if '/' in occ_url else occ_url
                    match = occupations_df[occupations_df.iloc[:, 0].str.contains(occ_id, na=False)]
                    if not match.empty:
                        if using_new_schema:
                            # Use clean preferred_name from new schema
                            preferred_name = match.iloc[0]['preferred_name']
                            main_name = preferred_name
                        else:
                            # Fallback to old parsing method
                            description = match.iloc[0, 1].strip().strip('"')
                            main_name = self._extract_occupation_name(description)
                        
                        decoded_occupations.append({
                            "id": occ_url,
                            "description": main_name
                        })
                    else:
                        decoded_occupations.append({
                            "id": occ_url,
                            "description": occ_id
                        })
            
            return {
                "skills": decoded_skills,
                "occupations": decoded_occupations
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to decode ESCO data: {str(e)}")

    return app