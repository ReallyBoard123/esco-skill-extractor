"""
Intelligent CV Analyzer - Combines BGE-M3 + Gemma3 4B for comprehensive analysis
"""

import time
from typing import Dict, List, Any
from collections import defaultdict
from .extractor import ESCOExtractor
from .cv_intelligence import CVIntelligenceEngine
from .gemma_provider import Gemma3Provider

class IntelligentCVAnalyzer:
    """Main analyzer that combines BGE-M3 precision with Gemma3 4B intelligence"""
    
    def __init__(self):
        """Initialize both BGE-M3 and Gemma3 systems"""
        print("🚀 Initializing Intelligent CV Analyzer...")
        
        # BGE-M3 for precise ESCO skill matching
        self.esco_extractor = ESCOExtractor()
        
        # Gemma3 4B for context understanding  
        self.gemma_provider = Gemma3Provider()
        
        # Intelligence engine for job/career analysis
        self.cv_intelligence = CVIntelligenceEngine(self.esco_extractor)
        
        print("✅ Intelligent CV Analyzer ready")
    
    def analyze_pdf_cv(self, pdf_content: bytes) -> Dict[str, Any]:
        """Complete intelligent analysis of PDF CV without prefilter"""
        
        analysis_start = time.time()
        
        # Step 1: Extract text from PDF
        import fitz
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        try:
            cv_text = ""
            page_count = pdf_document.page_count
            for page_num in range(page_count):
                page = pdf_document[page_num]
                cv_text += page.get_text() + "\n"
        finally:
            pdf_document.close()
        
        cv_text = cv_text.strip()
        
        if not cv_text:
            return {"error": "No text could be extracted from PDF"}
        
        return self.analyze_text_cv(cv_text, {
            "source": "pdf",
            "pages": page_count,
            "text_length": len(cv_text)
        })

    def analyze_pdf_cv_prefiltered(
        self,
        pdf_content: bytes,
        skills_threshold: float = None,
        occupations_threshold: float = None,
        max_results: int = None
    ) -> Dict[str, Any]:
        """Complete intelligent analysis of PDF CV with Gemma prefilter"""
        import fitz
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        try:
            cv_text = ""
            page_count = pdf_document.page_count
            for page_num in range(page_count):
                page = pdf_document[page_num]
                cv_text += page.get_text() + "\n"
        finally:
            pdf_document.close()

        cv_text = cv_text.strip()
        if not cv_text:
            return {"error": "No text could be extracted from PDF"}

        filter_result = self.gemma_provider.filter_professional_sentences(cv_text)
        filtered_text = filter_result.get("filtered_text") or cv_text

        analysis = self.analyze_text_cv(filtered_text, {
            "source": "pdf_prefiltered",
            "pages": page_count,
            "text_length": len(filtered_text),
            "original_text_length": len(cv_text)
        }, skills_threshold=skills_threshold, occupations_threshold=occupations_threshold, max_results=max_results)
        analysis["filter_summary"] = filter_result
        return analysis
    
    def analyze_text_cv(
        self,
        cv_text: str,
        metadata: Dict = None,
        skills_threshold: float = None,
        occupations_threshold: float = None,
        max_results: int = None
    ) -> Dict[str, Any]:
        """Complete intelligent analysis of CV text"""
        
        if metadata is None:
            metadata = {"source": "text", "text_length": len(cv_text)}
        
        analysis_steps = {
            "step1_bge_extraction": 0,
            "step2_gemma_sections": 0, 
            "step3_gemma_contexts": 0,
            "step4_job_matching": 0,
            "step5_career_prediction": 0,
            "step6_recommendations": 0
        }
        
        # Step 1: BGE-M3 for precise ESCO skill extraction
        step_start = time.time()
        print("🔍 Step 1: Extracting ESCO skills with BGE-M3...")
        
        skill_threshold = skills_threshold if skills_threshold is not None else self.esco_extractor.skills_threshold
        occupation_threshold = occupations_threshold if occupations_threshold is not None else self.esco_extractor.occupation_threshold
        max_skills = max_results or 30
        max_occupations = min(max_skills, 30)

        extracted_skills = self.esco_extractor.extract_skills(
            cv_text,
            threshold=skill_threshold,
            max_results=max_skills
        )
        extracted_occupations = self.esco_extractor.extract_occupations(
            cv_text,
            threshold=occupation_threshold,
            max_results=max_occupations
        )
        
        analysis_steps["step1_bge_extraction"] = time.time() - step_start
        print(f"✅ Found {len(extracted_skills)} skills, {len(extracted_occupations)} occupations")
        
        # Step 2: Gemma3 4B for CV section parsing
        step_start = time.time()
        print("🧠 Step 2: Parsing CV sections with Gemma3 4B...")
        
        cv_sections = self.gemma_provider.parse_cv_sections(cv_text)
        
        analysis_steps["step2_gemma_sections"] = time.time() - step_start
        print(f"✅ Identified {len(cv_sections)} CV sections")
        
        # Step 3: Gemma3 4B for skill context analysis
        step_start = time.time()
        print("🧠 Step 3: Analyzing skill contexts with Gemma3 4B...")
        
        skill_names = [skill['name'] for skill in extracted_skills]
        skill_contexts = self.gemma_provider.analyze_skill_contexts(cv_text, skill_names)
        
        analysis_steps["step3_gemma_contexts"] = time.time() - step_start
        print(f"✅ Analyzed context for {len(skill_contexts)} skills")
        
        # Step 4: Intelligent job matching using ESCO relationships
        step_start = time.time()
        print("🎯 Step 4: Finding job matches...")
        
        # Convert BGE-M3 results to SkillMatch objects for intelligence engine
        from .cv_intelligence import SkillMatch
        skill_matches = []
        for skill in extracted_skills:
            # Find context for this skill
            skill_context = next((ctx for ctx in skill_contexts if ctx.skill_name.lower() in skill['name'].lower()), None)
            
            skill_match = SkillMatch(
                uri=skill['uri'],
                name=skill['name'],
                similarity=skill['similarity'],
                context=skill_context.context_description if skill_context else f"Extracted from CV: {skill['name']}",
                section=self._determine_skill_section(skill['name'], cv_sections),
                categories=self.cv_intelligence.skill_categories.get(skill['uri'], []),
                skill_type=self.esco_extractor._skill_data.get(skill['uri'], {}).get('type', 'unknown')
            )
            skill_matches.append(skill_match)
        
        current_job_matches = self.cv_intelligence._find_job_matches(skill_matches)
        job_match_dicts = [self.cv_intelligence._job_match_to_dict(job) for job in current_job_matches[:10]]
        
        analysis_steps["step4_job_matching"] = time.time() - step_start
        print(f"✅ Found {len(current_job_matches)} job matches")
        
        # Step 5: Career opportunity prediction
        step_start = time.time()
        print("🚀 Step 5: Predicting career opportunities...")
        
        career_opportunities = self.cv_intelligence._predict_career_opportunities(skill_matches)
        skill_gap_analysis = self.cv_intelligence._analyze_skill_gaps(skill_matches, career_opportunities)
        
        analysis_steps["step5_career_prediction"] = time.time() - step_start
        print(f"✅ Identified {len(career_opportunities)} career opportunities")
        
        # Step 6: Gemma3 4B for intelligent recommendations
        step_start = time.time()
        print("🧠 Step 6: Generating recommendations with Gemma3 4B...")
        
        skill_prompt_data = [
            {
                "name": skill["name"],
                "similarity": skill.get("similarity"),
                "matched_token": skill.get("matched_token"),
                "description": skill.get("description", "")
            }
            for skill in extracted_skills
        ]
        occupation_prompt_data = [
            {
                "name": occ["name"],
                "similarity": occ.get("similarity"),
                "description": occ.get("description", "")
            }
            for occ in extracted_occupations
        ]
        intelligent_recommendations = self.gemma_provider.generate_career_options(
            skill_prompt_data,
            occupation_prompt_data,
            skill_gap_analysis.get("current_skill_categories", {})
        )
        
        # Add German translations for job search
        for rec in intelligent_recommendations:
            if rec.get("role"):
                rec["german_role"] = self.gemma_provider.translate_role_to_german(rec["role"])
        
        analysis_steps["step6_recommendations"] = time.time() - step_start
        print(f"✅ Generated {len(intelligent_recommendations)} recommendations with German translations")
        
        # Compile comprehensive results
        total_time = sum(analysis_steps.values())
        
        role_fit_insights = self.gemma_provider.generate_role_fit_overview(job_match_dicts)
        
        # Add German translations to role fit insights
        for insight in role_fit_insights:
            if insight.get("role"):
                insight["german_role"] = self.gemma_provider.translate_role_to_german(insight["role"])
                
        # Generate city suggestions based on CV analysis
        skill_names = [skill['name'] for skill in extracted_skills[:10]]
        role_names = [rec.get('role', '') for rec in intelligent_recommendations[:3]]
        city_suggestions = self.gemma_provider.suggest_job_cities(cv_text, skill_names, role_names)

        return {
            "analysis_summary": {
                "source": metadata.get("source", "unknown"),
                "processing_time": f"{total_time:.2f}s",
                "performance_breakdown": analysis_steps,
                "cv_metadata": metadata,
                "skills_found": len(extracted_skills),
                "occupations_found": len(extracted_occupations), 
                "sections_parsed": len(cv_sections),
                "job_matches": len(current_job_matches),
                "career_opportunities": len(career_opportunities)
            },
            
            # Core extraction results (BGE-M3)
            "extracted_skills": [
                {
                    **skill,
                    "categories": self.cv_intelligence.skill_categories.get(skill['uri'], []),
                    "skill_type": self.esco_extractor._skill_data.get(skill['uri'], {}).get('type', 'unknown')
                }
                for skill in extracted_skills
            ],
            
            "extracted_occupations": [
                {
                    **occ,
                    "isco_group": self.esco_extractor._occupation_data.get(occ['uri'], {}).get('iscoGroup', ''),
                    "description": self.esco_extractor._occupation_data.get(occ['uri'], {}).get('description', '')[:200] + "..."
                }
                for occ in extracted_occupations
            ],
            
            # Enhanced analysis (Gemma3 4B)
            "cv_sections": {
                section_name: {
                    "section_type": section.section_type,
                    "items_count": len(section.items),
                    "key_items": section.items[:3]  # Show top 3 items
                }
                for section_name, section in cv_sections.items()
            },
            
            "skill_contexts": [
                {
                    "skill_name": ctx.skill_name,
                    "proficiency_level": ctx.proficiency_level,
                    "years_experience": ctx.years_experience,
                    "context_description": ctx.context_description,
                    "used_in_role": ctx.used_in_role,
                    "industry_context": ctx.industry_context
                }
                for ctx in skill_contexts
            ],
            
            # Job matching results (ESCO Intelligence)
            "current_job_matches": job_match_dicts,
            
            "career_opportunities": [
                self.cv_intelligence._opportunity_to_dict(opp)
                for opp in career_opportunities[:15]
            ],
            
            # Analysis insights
            "skill_gap_analysis": skill_gap_analysis,
            
            # AI recommendations (Gemma3 4B)
            "intelligent_recommendations": intelligent_recommendations,
            
            # City suggestions for job search
            "city_suggestions": city_suggestions,
            
            # Summary insights
            "insights": {
                "strongest_skill_categories": self._get_top_categories(skill_matches),
                "experience_level": self._infer_experience_level(skill_contexts),
                "career_focus_suggestions": self._suggest_career_focus(career_opportunities),
                "next_steps": intelligent_recommendations[:3]  # Top 3 recommendations
            },
            "career_role_insights": role_fit_insights
        }

    def analyze_text_cv_prefiltered(
        self,
        cv_text: str,
        metadata: Dict = None,
        skills_threshold: float = None,
        occupations_threshold: float = None,
        max_results: int = None
    ) -> Dict[str, Any]:
        """Run analysis after using Gemma to pre-filter relevant text"""
        filter_result = self.gemma_provider.filter_professional_sentences(cv_text)
        filtered_text = filter_result.get("filtered_text") or cv_text
        kept = filter_result.get("kept_sentences", [])
        dropped = filter_result.get("dropped_sentences", [])
        location_hint = self.gemma_provider.infer_location(cv_text)

        # Prepare metadata noting filtering
        updated_metadata = dict(metadata or {})
        updated_metadata.setdefault("source", "text_prefiltered")
        updated_metadata["text_length"] = len(filtered_text)
        updated_metadata["original_text_length"] = len(cv_text)

        result = self.analyze_text_cv(
            filtered_text,
            updated_metadata,
            skills_threshold=skills_threshold,
            occupations_threshold=occupations_threshold,
            max_results=max_results
        )
        result["filter_summary"] = {
            "mode": "gemma_pre_filter",
            "kept_sentences": kept,
            "dropped_sentences": dropped,
            "notes": filter_result.get("notes", ""),
            "keep_ids": filter_result.get("keep_ids", []),
            "drop_ids": filter_result.get("drop_ids", []),
            "total_sentences": filter_result.get("total_sentences"),
            "evaluated_sentences": filter_result.get("evaluated_sentences"),
            "filtered_text_preview": filtered_text[:300]
        }
        if location_hint:
            result["location_hint"] = location_hint
        return result
    
    def _determine_skill_section(self, skill_name: str, cv_sections: Dict) -> str:
        """Determine which CV section a skill likely came from"""
        skill_lower = skill_name.lower()
        
        for section_name, section in cv_sections.items():
            for item in section.items:
                # Check if skill appears in any field of the section
                for value in item.values():
                    if skill_lower in str(value).lower():
                        return section_name
        
        return "general"
    
    def _get_top_categories(self, skill_matches: List) -> List[str]:
        """Get top skill categories from matches"""
        from collections import defaultdict
        
        category_counts = defaultdict(int)
        for skill in skill_matches:
            for category in skill.categories:
                category_counts[category] += 1
        
        return sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    def _infer_experience_level(self, skill_contexts: List) -> str:
        """Infer overall experience level from skill contexts"""
        level_counts = defaultdict(int)
        
        for ctx in skill_contexts:
            if ctx.proficiency_level:
                level_counts[ctx.proficiency_level] += 1
        
        if not level_counts:
            return "intermediate"
        
        # Return most common level
        return max(level_counts.items(), key=lambda x: x[1])[0]
    
    def _suggest_career_focus(self, opportunities: List) -> List[str]:
        """Suggest career focus areas based on opportunities"""
        from collections import defaultdict
        
        category_opportunities = defaultdict(int)
        
        for opp in opportunities[:10]:  # Top 10 opportunities
            for category in opp.category_focus:
                category_opportunities[category] += 1
        
        # Return top 3 categories with most opportunities
        top_categories = sorted(category_opportunities.items(), key=lambda x: x[1], reverse=True)[:3]
        return [f"{cat} skills ({count} opportunities)" for cat, count in top_categories]
