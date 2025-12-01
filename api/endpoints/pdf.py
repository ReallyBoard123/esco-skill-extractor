"""PDF processing endpoints"""

import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

router = APIRouter()


@router.post("/extract-pdf-skills", tags=["PDF Extraction"])
async def extract_pdf_skills(
    pdf: UploadFile = File(...),
    skills_threshold: float = Form(0.6),
    occupations_threshold: float = Form(0.55),
    max_results: int = Form(10),
    rich_data: bool = Form(False),
    extractor=None
) -> Dict[str, Any]:
    """Extract skills and occupations from uploaded PDF"""
    if not pdf.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        import fitz  # PyMuPDF
        
        # Extract PDF text
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
        
        if rich_data:
            # Rich extraction
            start_time = time.time()
            
            skill_matches = extractor.extract_skills(
                cleaned_text,
                threshold=skills_threshold,
                max_results=max_results
            )
            
            occupation_matches = extractor.extract_occupations(
                cleaned_text,
                threshold=occupations_threshold,
                max_results=max_results
            )
            
            # Enrich data
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
                    "filename": pdf.filename,
                    "pages": page_count,
                    "text_length": len(cleaned_text),
                    "totalSkillsFound": len(rich_skills),
                    "totalOccupationsFound": len(rich_occupations),
                    "processingTime": f"{processing_time:.2f}s",
                    "rich_data": True
                }
            }
        else:
            # Basic extraction
            skill_matches = extractor.extract_skills(
                cleaned_text,
                threshold=skills_threshold,
                max_results=max_results
            )
            
            occupation_matches = extractor.extract_occupations(
                cleaned_text,
                threshold=occupations_threshold,
                max_results=max_results
            )
            
            return {
                "skills": [skill['name'] for skill in skill_matches],
                "occupations": [occ['name'] for occ in occupation_matches],
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