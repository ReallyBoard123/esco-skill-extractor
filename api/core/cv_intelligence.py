"""
Intelligent CV Analysis System for ESCO Skill-to-Career Matching
Uses ESCO occupation-skill relationships for job matching and career prediction
"""

import csv
import json
import re
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from pathlib import Path

from .config import ESCO_CSV_ROOT
from .extractor import ESCOExtractor

@dataclass
class SkillMatch:
    """Represents a skill found in CV with context"""
    uri: str
    name: str
    similarity: float
    context: str  # Where in CV it was found
    section: str  # CV section (experience, education, skills)
    categories: List[str]
    skill_type: str  # knowledge, skill/competence, etc.

@dataclass
class JobMatch:
    """Represents a job that matches CV skills"""
    uri: str
    name: str
    isco_group: str
    description: str
    match_score: float
    matched_skills: List[str]
    missing_essential: List[str]
    missing_optional: List[str]
    skill_coverage: Dict[str, float]  # {'essential': 0.8, 'optional': 0.4}

@dataclass
class CareerOpportunity:
    """Represents a potential career path with skill gaps"""
    job: JobMatch
    skills_to_gain: List[str]
    effort_level: str  # 'low', 'medium', 'high'
    category_focus: List[str]  # ['digital', 'green'] - what skill types to focus on
    estimated_time: str  # '3-6 months', '1-2 years'

class CVIntelligenceEngine:
    """Intelligent CV analysis using ESCO relationships"""
    
    def __init__(self, extractor: ESCOExtractor = None):
        """Initialize with ESCO extractor and load relationship data"""
        self.extractor = extractor or ESCOExtractor()
        
        # Data structures for intelligent matching
        self.occupation_skills = {}  # occupation_uri -> {'essential': [skills], 'optional': [skills]}
        self.skill_occupations = {}  # skill_uri -> [occupation_uris] 
        self.skill_categories = {}   # skill_uri -> [categories]
        self.occupation_data = {}    # occupation_uri -> occupation details
        
        # Load ESCO relationship data
        self._load_esco_relationships()
        
    def _load_esco_relationships(self):
        """Load ESCO occupation-skill relationships from CSV files"""
        print("🔄 Loading ESCO relationships for intelligent matching...")
        
        # Load occupation-skill relationships
        relations_file = ESCO_CSV_ROOT / "occupationSkillRelations_en.csv"
        with open(relations_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                occ_uri = row['occupationUri']
                skill_uri = row['skillUri']
                relation_type = row['relationType']  # essential/optional
                
                # Build occupation -> skills mapping
                if occ_uri not in self.occupation_skills:
                    self.occupation_skills[occ_uri] = {'essential': [], 'optional': []}
                self.occupation_skills[occ_uri][relation_type].append(skill_uri)
                
                # Build skill -> occupations mapping
                if skill_uri not in self.skill_occupations:
                    self.skill_occupations[skill_uri] = []
                self.skill_occupations[skill_uri].append(occ_uri)
        
        # Load skill categories from collection files
        category_files = {
            'digital': 'digitalSkillsCollection_en.csv',
            'green': 'greenSkillsCollection_en.csv', 
            'transversal': 'transversalSkillsCollection_en.csv',
            'language': 'languageSkillsCollection_en.csv',
            'research': 'researchSkillsCollection_en.csv',
            'digComp': 'digCompSkillsCollection_en.csv'
        }
        
        for category, filename in category_files.items():
            file_path = ESCO_CSV_ROOT / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        skill_uri = row['conceptUri']
                        if skill_uri not in self.skill_categories:
                            self.skill_categories[skill_uri] = []
                        self.skill_categories[skill_uri].append(category)
        
        # Load occupation details
        occupations_file = ESCO_CSV_ROOT / "occupations_en.csv"
        with open(occupations_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.occupation_data[row['conceptUri']] = {
                    'name': row['preferredLabel'],
                    'description': row.get('description', ''),
                    'isco_group': row.get('iscoGroup', ''),
                    'alternatives': self._parse_alternatives(row.get('altLabels', ''))
                }
        
        print(f"✅ Loaded {len(self.occupation_skills)} occupation-skill relationships")
        print(f"✅ Loaded {len(self.skill_categories)} categorized skills")
    
    def _parse_alternatives(self, alt_labels: str) -> List[str]:
        """Parse alternative labels from CSV field"""
        if not alt_labels or not alt_labels.strip():
            return []
        return [alt.strip() for alt in alt_labels.split('\n') if alt.strip()]
    
    def analyze_cv_pdf(self, pdf_content: bytes) -> Dict:
        """Complete intelligent CV analysis from PDF"""
        import fitz
        
        # Extract text from PDF
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        try:
            cv_text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                cv_text += page.get_text() + "\n"
        finally:
            pdf_document.close()
        
        return self.analyze_cv_text(cv_text.strip())
    
    def analyze_cv_text(self, cv_text: str) -> Dict:
        """Complete intelligent CV analysis from text"""
        
        # 1. Parse CV into sections
        cv_sections = self._parse_cv_sections(cv_text)
        
        # 2. Extract skills with context
        skill_matches = self._extract_contextual_skills(cv_text, cv_sections)
        
        # 3. Find current job matches
        current_jobs = self._find_job_matches(skill_matches)
        
        # 4. Predict career opportunities
        career_opportunities = self._predict_career_opportunities(skill_matches)
        
        # 5. Analyze skill gaps
        skill_gap_analysis = self._analyze_skill_gaps(skill_matches, career_opportunities)
        
        return {
            "cv_analysis": {
                "sections_found": list(cv_sections.keys()),
                "total_skills_identified": len(skill_matches),
                "skill_categories": self._get_skill_category_breakdown(skill_matches)
            },
            "extracted_skills": [self._skill_match_to_dict(s) for s in skill_matches],
            "current_job_matches": [self._job_match_to_dict(j) for j in current_jobs[:10]],
            "career_opportunities": [self._opportunity_to_dict(o) for o in career_opportunities[:15]],
            "skill_gap_analysis": skill_gap_analysis,
            "recommendations": self._generate_recommendations(skill_matches, career_opportunities)
        }
    
    def _parse_cv_sections(self, cv_text: str) -> Dict[str, str]:
        """Parse CV text into logical sections"""
        sections = {}
        
        # Common section patterns
        section_patterns = {
            'experience': r'(?i)(work\s+experience|professional\s+experience|employment|career\s+history)',
            'education': r'(?i)(education|academic|qualification|degree|university|college)',
            'skills': r'(?i)(skills|competencies|technical\s+skills|technologies)',
            'projects': r'(?i)(projects|portfolio|achievements)',
            'certifications': r'(?i)(certifications?|certificates?|licenses?)'
        }
        
        # Split text by common section headers
        lines = cv_text.split('\n')
        current_section = 'general'
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line is a section header
            section_found = None
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line) and len(line) < 50:  # Likely a header
                    section_found = section_name
                    break
            
            if section_found:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = section_found
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_contextual_skills(self, cv_text: str, cv_sections: Dict[str, str]) -> List[SkillMatch]:
        """Extract skills with their context from CV"""
        all_skill_matches = []
        
        # Extract skills from full text using existing extractor
        raw_skills = self.extractor.extract_skills(cv_text, max_results=50)
        
        # Enhance each skill with context information
        for skill in raw_skills:
            skill_uri = skill['uri']
            skill_name = skill['name']
            similarity = skill['similarity']
            
            # Find which section(s) contain this skill
            context_info = self._find_skill_context(skill_name, cv_sections)
            
            # Get skill categories
            categories = self.skill_categories.get(skill_uri, [])
            
            # Get skill type from extractor's data
            skill_data = self.extractor._skill_data.get(skill_uri, {})
            skill_type = skill_data.get('type', 'unknown')
            
            skill_match = SkillMatch(
                uri=skill_uri,
                name=skill_name,
                similarity=similarity,
                context=context_info['context'],
                section=context_info['section'],
                categories=categories,
                skill_type=skill_type
            )
            
            all_skill_matches.append(skill_match)
        
        return all_skill_matches
    
    def _find_skill_context(self, skill_name: str, cv_sections: Dict[str, str]) -> Dict[str, str]:
        """Find where and how a skill is mentioned in the CV"""
        
        # Look for skill mention in each section
        for section_name, section_text in cv_sections.items():
            if skill_name.lower() in section_text.lower():
                # Find the specific sentence/context
                sentences = re.split(r'[.!?\n]', section_text)
                for sentence in sentences:
                    if skill_name.lower() in sentence.lower():
                        return {
                            'section': section_name,
                            'context': sentence.strip()[:200]  # First 200 chars
                        }
        
        # Default if not found in specific section
        return {
            'section': 'general',
            'context': f"Skill identified: {skill_name}"
        }
    
    def _find_job_matches(self, skill_matches: List[SkillMatch]) -> List[JobMatch]:
        """Find jobs that match current skills"""
        user_skill_uris = {skill.uri for skill in skill_matches}
        job_matches = []
        
        for occ_uri, skill_requirements in self.occupation_skills.items():
            essential_skills = set(skill_requirements['essential'])
            optional_skills = set(skill_requirements['optional'])
            
            # Calculate coverage
            essential_match = user_skill_uris & essential_skills
            optional_match = user_skill_uris & optional_skills
            
            # Only consider jobs where user has some essential skills
            if len(essential_match) > 0:
                essential_coverage = len(essential_match) / len(essential_skills) if essential_skills else 0
                optional_coverage = len(optional_match) / len(optional_skills) if optional_skills else 0
                
                # Calculate overall match score (weighted towards essential skills)
                match_score = (essential_coverage * 0.7) + (optional_coverage * 0.3)
                
                # Get job details
                job_data = self.occupation_data.get(occ_uri, {})
                
                # Find missing skills
                missing_essential = [self.extractor._skill_data[uri]['name'] 
                                   for uri in (essential_skills - user_skill_uris)
                                   if uri in self.extractor._skill_data]
                missing_optional = [self.extractor._skill_data[uri]['name']
                                  for uri in (optional_skills - user_skill_uris)
                                  if uri in self.extractor._skill_data]
                
                matched_skill_names = [skill.name for skill in skill_matches 
                                     if skill.uri in (essential_match | optional_match)]
                
                job_match = JobMatch(
                    uri=occ_uri,
                    name=job_data.get('name', 'Unknown'),
                    isco_group=job_data.get('isco_group', ''),
                    description=job_data.get('description', ''),
                    match_score=match_score,
                    matched_skills=matched_skill_names,
                    missing_essential=missing_essential,
                    missing_optional=missing_optional,
                    skill_coverage={
                        'essential': essential_coverage,
                        'optional': optional_coverage
                    }
                )
                
                job_matches.append(job_match)
        
        # Sort by match score
        return sorted(job_matches, key=lambda x: x.match_score, reverse=True)
    
    def _predict_career_opportunities(self, skill_matches: List[SkillMatch]) -> List[CareerOpportunity]:
        """Predict career opportunities if additional skills are gained"""
        opportunities = []
        user_skill_uris = {skill.uri for skill in skill_matches}
        
        for occ_uri, skill_requirements in self.occupation_skills.items():
            essential_skills = set(skill_requirements['essential'])
            optional_skills = set(skill_requirements['optional'])
            
            essential_match = user_skill_uris & essential_skills
            essential_missing = essential_skills - user_skill_uris
            
            # Look for jobs where user has good foundation but missing some key skills
            if len(essential_match) >= 1 and len(essential_missing) <= 5:  # Manageable gap
                job_data = self.occupation_data.get(occ_uri, {})
                
                # Determine skills to gain
                skills_to_gain = [self.extractor._skill_data[uri]['name']
                                for uri in essential_missing
                                if uri in self.extractor._skill_data]
                
                # Determine effort level based on number of missing skills
                if len(essential_missing) <= 2:
                    effort_level = 'low'
                    estimated_time = '3-6 months'
                elif len(essential_missing) <= 4:
                    effort_level = 'medium' 
                    estimated_time = '6-12 months'
                else:
                    effort_level = 'high'
                    estimated_time = '1-2 years'
                
                # Determine category focus
                category_focus = []
                for skill_uri in essential_missing:
                    categories = self.skill_categories.get(skill_uri, [])
                    category_focus.extend(categories)
                category_focus = list(set(category_focus))  # Remove duplicates
                
                # Create job match for this opportunity
                current_coverage = len(essential_match) / len(essential_skills)
                
                job_match = JobMatch(
                    uri=occ_uri,
                    name=job_data.get('name', 'Unknown'),
                    isco_group=job_data.get('isco_group', ''),
                    description=job_data.get('description', ''),
                    match_score=current_coverage,
                    matched_skills=[skill.name for skill in skill_matches if skill.uri in essential_match],
                    missing_essential=skills_to_gain,
                    missing_optional=[],
                    skill_coverage={'essential': current_coverage, 'optional': 0}
                )
                
                opportunity = CareerOpportunity(
                    job=job_match,
                    skills_to_gain=skills_to_gain,
                    effort_level=effort_level,
                    category_focus=category_focus,
                    estimated_time=estimated_time
                )
                
                opportunities.append(opportunity)
        
        # Sort by potential (fewer skills needed = better opportunity)
        return sorted(opportunities, key=lambda x: (len(x.skills_to_gain), -x.job.match_score))
    
    def _analyze_skill_gaps(self, skill_matches: List[SkillMatch], opportunities: List[CareerOpportunity]) -> Dict:
        """Analyze skill gaps for career advancement"""
        
        # Count skills by category
        current_categories = defaultdict(int)
        for skill in skill_matches:
            for category in skill.categories:
                current_categories[category] += 1
        
        # Analyze most needed skills across opportunities
        skill_demand = defaultdict(int)
        category_demand = defaultdict(int)
        
        for opp in opportunities[:10]:  # Top 10 opportunities
            for skill_name in opp.skills_to_gain:
                skill_demand[skill_name] += 1
            for category in opp.category_focus:
                category_demand[category] += 1
        
        return {
            "current_skill_categories": dict(current_categories),
            "most_demanded_skills": sorted(skill_demand.items(), key=lambda x: x[1], reverse=True)[:10],
            "most_demanded_categories": sorted(category_demand.items(), key=lambda x: x[1], reverse=True),
            "category_recommendations": self._generate_category_recommendations(current_categories, category_demand)
        }
    
    def _generate_category_recommendations(self, current: Dict, demand: Dict) -> List[str]:
        """Generate recommendations for skill category development"""
        recommendations = []
        
        for category, demand_count in demand.items():
            current_count = current.get(category, 0)
            if demand_count > 2 and current_count < 3:  # High demand, low current skills
                recommendations.append(f"Focus on {category} skills - high demand with {demand_count} opportunities")
        
        return recommendations
    
    def _generate_recommendations(self, skills: List[SkillMatch], opportunities: List[CareerOpportunity]) -> List[str]:
        """Generate actionable career recommendations"""
        recommendations = []
        
        # Skill diversity recommendation
        categories_count = len(set(cat for skill in skills for cat in skill.categories))
        if categories_count < 3:
            recommendations.append("Consider diversifying skills across more categories (digital, green, transversal)")
        
        # Quick wins
        easy_opportunities = [opp for opp in opportunities[:5] if opp.effort_level == 'low']
        if easy_opportunities:
            rec_skills = easy_opportunities[0].skills_to_gain[:2]
            recommendations.append(f"Quick career boost: Learn {', '.join(rec_skills)} (3-6 months)")
        
        # Long-term growth
        high_value_opportunities = [opp for opp in opportunities[:3] if len(opp.skills_to_gain) >= 3]
        if high_value_opportunities:
            job_name = high_value_opportunities[0].job.name
            recommendations.append(f"Long-term goal: Aim for {job_name} role with strategic skill development")
        
        return recommendations
    
    def _get_skill_category_breakdown(self, skills: List[SkillMatch]) -> Dict[str, int]:
        """Get breakdown of skills by category"""
        category_counts = defaultdict(int)
        for skill in skills:
            for category in skill.categories:
                category_counts[category] += 1
        return dict(category_counts)
    
    # Helper methods to convert objects to dictionaries for API responses
    def _skill_match_to_dict(self, skill: SkillMatch) -> Dict:
        return {
            "name": skill.name,
            "uri": skill.uri,
            "similarity": skill.similarity,
            "context": skill.context,
            "section": skill.section,
            "categories": skill.categories,
            "skill_type": skill.skill_type
        }
    
    def _job_match_to_dict(self, job: JobMatch) -> Dict:
        return {
            "name": job.name,
            "uri": job.uri,
            "isco_group": job.isco_group,
            "description": job.description[:200] + "..." if len(job.description) > 200 else job.description,
            "match_score": round(job.match_score, 3),
            "matched_skills": job.matched_skills,
            "missing_essential": job.missing_essential,
            "missing_optional": job.missing_optional[:5],  # Limit for API response
            "skill_coverage": job.skill_coverage
        }
    
    def _opportunity_to_dict(self, opp: CareerOpportunity) -> Dict:
        return {
            "job": self._job_match_to_dict(opp.job),
            "skills_to_gain": opp.skills_to_gain,
            "effort_level": opp.effort_level,
            "category_focus": opp.category_focus,
            "estimated_time": opp.estimated_time
        }