"""
Gemma3 4B Provider for CV Context Understanding
Handles intelligent text analysis that embeddings can't do
"""

import re
import json
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from .prefilter_retriever import PrefilterRetriever
from .config import DATA_DIR

@dataclass 
class CVSection:
    """Represents a parsed CV section with metadata"""
    section_type: str  # experience, education, skills, projects
    content: str
    items: List[Dict[str, Any]]  # Structured data extracted from section

@dataclass
class SkillContext:
    """Enhanced skill context from Gemma3 analysis"""
    skill_name: str
    proficiency_level: str  # beginner, intermediate, advanced, expert
    years_experience: Optional[str]
    context_description: str
    used_in_role: Optional[str]
    industry_context: Optional[str]

class Gemma3Provider:
    """Provider for Gemma3 4B intelligent CV analysis"""
    
    def __init__(self, model_name: str = "gemma3:4b", ollama_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url
        try:
            examples_path = DATA_DIR / "prefilter_examples.json"
            if examples_path.exists():
                self.prefilter_retriever = PrefilterRetriever(examples_path)
            else:
                self.prefilter_retriever = None
        except Exception as e:
            print(f"Prefilter retriever unavailable: {e}")
            self.prefilter_retriever = None
    
    def _call_gemma(self, prompt: str) -> str:
        """Make request to Ollama Gemma3 4B"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()['response']
        except Exception as e:
            print(f"Gemma3 error: {e}")
            return ""
    
    def parse_cv_sections(self, cv_text: str) -> Dict[str, CVSection]:
        """Use Gemma3 to intelligently parse CV into sections"""
        
        prompt = f"""Analyze this CV and identify the main sections. For each section, extract structured information.

CV Text:
{cv_text[:2000]}  

Please analyze and return sections in this format:
SECTION: Work Experience
ITEMS: 
- Job Title: [title] | Company: [company] | Duration: [dates] | Description: [brief description]
- Job Title: [title] | Company: [company] | Duration: [dates] | Description: [brief description]

SECTION: Education  
ITEMS:
- Degree: [degree] | Institution: [school] | Year: [year] | Description: [brief description]

SECTION: Skills
ITEMS:
- Skill: [skill] | Level: [level] | Context: [how used]

SECTION: Projects
ITEMS:
- Project: [name] | Technologies: [tech] | Description: [brief description]

Be concise and extract only the most important information."""
        
        response = self._call_gemma(prompt)
        return self._parse_gemma_sections_response(response)
    
    def _parse_gemma_sections_response(self, response: str) -> Dict[str, CVSection]:
        """Parse Gemma3's structured response into CVSection objects"""
        sections = {}
        current_section = None
        current_items = []
        
        for line in response.split('\n'):
            line = line.strip()
            
            if line.startswith('SECTION:'):
                # Save previous section
                if current_section and current_items:
                    section_type = self._normalize_section_type(current_section)
                    sections[section_type] = CVSection(
                        section_type=section_type,
                        content=current_section,
                        items=current_items
                    )
                
                # Start new section
                current_section = line.replace('SECTION:', '').strip()
                current_items = []
                
            elif line.startswith('- ') and current_section:
                # Parse item
                item_text = line[2:]  # Remove "- "
                item_data = self._parse_item_text(item_text)
                if item_data:
                    current_items.append(item_data)
        
        # Save last section
        if current_section and current_items:
            section_type = self._normalize_section_type(current_section)
            sections[section_type] = CVSection(
                section_type=section_type,
                content=current_section,
                items=current_items
            )
        
        return sections
    
    def _normalize_section_type(self, section_name: str) -> str:
        """Normalize section names to standard types"""
        section_name = section_name.lower()
        
        if any(word in section_name for word in ['work', 'experience', 'employment', 'career']):
            return 'experience'
        elif any(word in section_name for word in ['education', 'academic', 'degree', 'university']):
            return 'education'
        elif any(word in section_name for word in ['skill', 'competenc', 'technical', 'technolog']):
            return 'skills'
        elif any(word in section_name for word in ['project', 'portfolio', 'achievement']):
            return 'projects'
        else:
            return 'other'
    
    def _parse_item_text(self, item_text: str) -> Optional[Dict[str, str]]:
        """Parse structured item text into dictionary"""
        # Split by | to get key-value pairs
        parts = [part.strip() for part in item_text.split('|')]
        item_data = {}
        
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                item_data[key.strip().lower()] = value.strip()
        
        return item_data if item_data else None
    
    def analyze_skill_contexts(self, cv_text: str, extracted_skills: List[str]) -> List[SkillContext]:
        """Use Gemma3 to understand context for each extracted skill"""
        
        skills_list = ', '.join(extracted_skills[:10])  # Limit for context
        
        prompt = f"""Analyze how each skill is used in this CV. For each skill, determine:
1. Proficiency level (beginner/intermediate/advanced/expert)
2. Years of experience (if mentioned)
3. Context of use (what projects/roles)
4. Industry application

CV Text:
{cv_text[:1500]}

Skills to analyze: {skills_list}

For each skill, respond in this format:
SKILL: [skill_name]
LEVEL: [proficiency_level]
YEARS: [years_experience or "not_specified"]
CONTEXT: [how and where used]
ROLE: [job title where used or "not_specified"]
INDUSTRY: [industry context or "general"]

Be specific and concise."""
        
        response = self._call_gemma(prompt)
        return self._parse_skill_contexts_response(response)
    
    def _parse_skill_contexts_response(self, response: str) -> List[SkillContext]:
        """Parse Gemma3's skill context analysis into SkillContext objects"""
        contexts = []
        current_skill = {}
        
        for line in response.split('\n'):
            line = line.strip()
            
            if line.startswith('SKILL:'):
                # Save previous skill
                if current_skill.get('skill_name'):
                    contexts.append(SkillContext(
                        skill_name=current_skill.get('skill_name', ''),
                        proficiency_level=current_skill.get('level', 'intermediate'),
                        years_experience=current_skill.get('years'),
                        context_description=current_skill.get('context', ''),
                        used_in_role=current_skill.get('role'),
                        industry_context=current_skill.get('industry')
                    ))
                
                # Start new skill
                current_skill = {
                    'skill_name': line.replace('SKILL:', '').strip()
                }
                
            elif ':' in line and current_skill:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if value and value.lower() != 'not_specified':
                    current_skill[key] = value
        
        # Save last skill
        if current_skill.get('skill_name'):
            contexts.append(SkillContext(
                skill_name=current_skill.get('skill_name', ''),
                proficiency_level=current_skill.get('level', 'intermediate'),
                years_experience=current_skill.get('years'),
                context_description=current_skill.get('context', ''),
                used_in_role=current_skill.get('role'),
                industry_context=current_skill.get('industry')
            ))
        
        return contexts
    
    def generate_career_recommendations(self, 
                                      current_skills: List[str], 
                                      career_opportunities: List[Dict],
                                      skill_gaps: Dict) -> List[str]:
        """Generate intelligent career recommendations using Gemma3"""
        
        top_opportunities = [opp['job']['name'] for opp in career_opportunities[:5]]
        missing_skills = skill_gaps.get('most_demanded_skills', [])
        
        prompt = f"""You are a career advisor. Based on this analysis, provide 3-5 specific, actionable career recommendations.

Current Skills: {', '.join(current_skills[:15])}

Top Career Opportunities: {', '.join(top_opportunities)}

Most Needed Skills: {', '.join([skill[0] for skill in missing_skills[:10]])}

Provide recommendations in this format:
RECOMMENDATION: [specific action]
TIMELINE: [timeframe]
BENEFIT: [career impact]

Focus on practical steps the person can take to advance their career."""
        
        response = self._call_gemma(prompt)
        return self._parse_recommendations_response(response)
    
    def _parse_recommendations_response(self, response: str) -> List[str]:
        """Parse Gemma3's recommendations into a list"""
        recommendations = []
        current_rec = {}
        
        for line in response.split('\n'):
            line = line.strip()
            
            if line.startswith('RECOMMENDATION:'):
                if current_rec.get('action'):
                    # Format previous recommendation
                    rec_text = current_rec['action']
                    if current_rec.get('timeline'):
                        rec_text += f" (Timeline: {current_rec['timeline']})"
                    if current_rec.get('benefit'):
                        rec_text += f" - {current_rec['benefit']}"
                    recommendations.append(rec_text)
                
                # Start new recommendation
                current_rec = {
                    'action': line.replace('RECOMMENDATION:', '').strip()
                }
                
            elif line.startswith('TIMELINE:') and current_rec:
                current_rec['timeline'] = line.replace('TIMELINE:', '').strip()
                
            elif line.startswith('BENEFIT:') and current_rec:
                current_rec['benefit'] = line.replace('BENEFIT:', '').strip()
        
        # Save last recommendation
        if current_rec.get('action'):
            rec_text = current_rec['action']
            if current_rec.get('timeline'):
                rec_text += f" (Timeline: {current_rec['timeline']})"
            if current_rec.get('benefit'):
                rec_text += f" - {current_rec['benefit']}"
            recommendations.append(rec_text)
        
        return recommendations

    def filter_professional_sentences(self, cv_text: str, max_sentences: int = 80) -> Dict[str, Any]:
        """Use Gemma3 to identify which sentences are professionally relevant"""

        sentences = self._split_into_sentences(cv_text)
        if not sentences:
            return {
                "filtered_text": cv_text,
                "kept_sentences": [],
                "dropped_sentences": [],
                "keep_ids": []
            }

        limited_sentences = sentences[:max_sentences]
        enumerated_text = "\n".join(f"{idx+1}. {sent}" for idx, sent in enumerate(limited_sentences))

        keep_ids: List[int] = []
        drop_ids: List[int] = []
        notes: List[str] = []
        classifications: List[Dict[str, Any]] = []

        for idx, sentence in enumerate(limited_sentences):
            label, reason = self._classify_sentence(sentence)
            classifications.append({
                "sentence": sentence,
                "label": label,
                "reason": reason
            })
            if label == "professional":
                keep_ids.append(idx + 1)
            else:
                drop_ids.append(idx + 1)
            if reason:
                notes.append(f"Sentence {idx+1}: {reason}")

        kept_sentences = [limited_sentences[i-1] for i in keep_ids if 0 < i <= len(limited_sentences)]
        dropped_sentences = [limited_sentences[i-1] for i in drop_ids if 0 < i <= len(limited_sentences)]

        filtered_text = "\n".join(kept_sentences) if kept_sentences else cv_text

        return {
            "filtered_text": filtered_text,
            "kept_sentences": kept_sentences,
            "dropped_sentences": dropped_sentences,
            "keep_ids": keep_ids,
            "drop_ids": drop_ids,
            "notes": " | ".join(notes)[:500],
            "total_sentences": len(sentences),
            "evaluated_sentences": len(limited_sentences),
            "classifications": classifications
        }

    def _split_into_sentences(self, text: str) -> List[str]:
        import re
        raw_sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
        sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 4]
        return sentences

    def _fallback_majority(self, sentence: str) -> Tuple[str, str]:
        if not self.prefilter_retriever:
            return "professional", "No retriever available"
        label = self.prefilter_retriever.majority_label(sentence)
        return label, "Retriever majority vote"

    def _build_sentence_context(self, sentence: str, top_k: int = 3) -> str:
        if not self.prefilter_retriever:
            return "(no retrieval context)"
        examples = self.prefilter_retriever.get_examples_for_sentence(sentence, top_k=top_k)
        if not examples:
            return "(no retrieval context)"
        lines = []
        for ex in examples:
            label = ex.get('label', 'professional')
            text = ex.get('text', '')
            reason = ex.get('reason', '')
            lines.append(f"- Label: {label} | Example: {text} | Reason: {reason}")
        return "\n".join(lines)

    def _classify_sentence(self, sentence: str) -> Tuple[str, str]:
        if not sentence.strip():
            return "personal", "Empty sentence"

        context = self._build_sentence_context(sentence)
        prompt = f"""Classify the following sentence from a CV. Respond ONLY with strict JSON.

Definitions:
- PROFESSIONAL: describes paid work experience, leadership, measurable achievements, education, certifications, consulting, or clearly monetized freelance/side businesses.
- PERSONAL: hobbies, leisure, personal interests, or activities with no evidence of clients, compensation, or impact relevant to the CV's professional narrative.
- If unsure whether a sentence is professional, prefer "personal" unless the text explicitly mentions clients, revenue, deliverables, or formal responsibility.

Similar labeled examples for context:
{context}

Sentence: "{sentence}"

JSON format:
{{"label": "professional" | "personal", "reason": "short explanation"}}
"""

        response = self._call_gemma(prompt)
        try:
            parsed = json.loads(self._extract_json_object(response))
            label = parsed.get('label', 'professional').strip().lower()
            if label not in {"professional", "personal"}:
                raise ValueError("Unknown label")
            reason = parsed.get('reason', '')
            return label, reason
        except Exception:
            label, reason = self._fallback_majority(sentence)
            return label, f"Fallback: {reason}"

    def _fallback_majority(self, sentence: str) -> Tuple[str, str]:
        if not self.prefilter_retriever:
            return "professional", "No retriever available"
        label = self.prefilter_retriever.majority_label(sentence)
        return label, "Retriever majority vote"

    def _extract_json_object(self, text: str) -> str:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return text

    def generate_career_options(self, skills: List[Dict[str, Any]], occupations: List[Dict[str, Any]], skill_categories: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        """Generate career suggestions using top skills and occupations"""
        if not skills or not occupations:
            return []

        top_skills = skills[:6]
        filtered_occupations = [occ for occ in occupations if (occ.get("similarity") or 0) >= 0.6]
        top_occupations = (filtered_occupations or occupations)[:5]

        skill_lines = []
        for idx, skill in enumerate(top_skills, start=1):
            snippet = skill.get("matched_token") or skill.get("description", "")
            skill_lines.append(
                f"{idx}. {skill.get('name')} (match {round(skill.get('similarity', 0)*100)}%) - {snippet}"
            )

        occupation_lines = []
        for idx, occ in enumerate(top_occupations, start=1):
            occupation_lines.append(
                f"{idx}. {occ.get('name')} (match {round(occ.get('similarity', 0)*100)}%) - {occ.get('description', '')[:140]}"
            )

        category_lines = []
        if skill_categories:
            for cat, count in sorted(skill_categories.items(), key=lambda x: x[1], reverse=True):
                category_lines.append(f"{cat}: {count}")

        prompt = f"""You are an expert career advisor. Based on the candidate's skills and ESCO occupations they matched, propose 3 REALISTIC, SINGLE-FOCUS career directions.

IMPORTANT RULES:
- Each role must be a SINGLE, real job title that exists in the job market
- NO combined roles (avoid "&", "and", "/") - each recommendation should be ONE specific job
- Use standard job titles that employers actually post (e.g., "Data Analyst", "Software Developer", "Marketing Manager")
- Focus on the candidate's STRONGEST skill area for each recommendation

Top skills:
{chr(10).join(skill_lines)}

Top occupations:
{chr(10).join(occupation_lines)}

Skill categories:
{chr(10).join(category_lines) if category_lines else "Not specified"}

For each career direction provide:
- role: single, realistic job title (e.g., "Data Analyst", NOT "Data Analyst & Business Consultant")
- why_it_fits: how the skills/occupations support this SPECIFIC role
- recommended_actions: list of concrete next steps (courses, projects, networking)
- skills_to_leverage: key strengths to emphasize
- skills_to_build: skills or experiences to acquire

Return STRICT JSON array in this format:
[
  {{"role":"...","why_it_fits":"...","recommended_actions":["..."],"skills_to_leverage":["..."],"skills_to_build":["..."]}}
]
"""

        response = self._call_gemma(prompt)
        try:
            text = response.strip()
            start = text.find('[')
            end = text.rfind(']')
            if start != -1 and end != -1 and end > start:
                text = text[start:end+1]
            insights = json.loads(text)
            if isinstance(insights, list):
                return insights
        except Exception:
            pass

        fallback = []
        for occ in top_occupations[:3]:
            fallback.append({
                "role": occ.get("name"),
                "why_it_fits": f"Matches {occ.get('similarity', 0)*100:.0f}% of required signals (e.g. {', '.join(s['name'] for s in top_skills[:2])}).",
                "recommended_actions": ["Deepen case studies showcasing these skills"],
                "skills_to_leverage": [s["name"] for s in top_skills[:3]],
                "skills_to_build": ["Research additional requirements for this occupation"]
            })
        return fallback

    def generate_role_fit_overview(self, job_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate narrative explaining why top job matches fit the candidate"""
        if not job_matches:
            return []

        top_jobs = job_matches[:5]
        job_lines = []
        for idx, job in enumerate(top_jobs, start=1):
            job_lines.append(
                f"{idx}. Role: {job.get('name')} | MatchScore: {round(job.get('match_score', 0)*100)}% | "
                f"MatchedSkills: {', '.join(job.get('matched_skills', [])[:6]) or 'None'} | "
                f"MissingSkills: {', '.join(job.get('missing_essential', [])[:5]) or 'None'}"
            )

        prompt = f"""You are an expert career coach. Given job matches and their matched/missing skills, explain in plain language why each role fits the candidate and what gaps remain.

Job Matches:
{chr(10).join(job_lines)}

Respond ONLY with JSON array of objects using this schema:
[
  {{"role": "...", "why_it_fits": "...", "skills_to_highlight": ["..."], "gaps_to_address": ["..."]}}
]
"""

        response = self._call_gemma(prompt)
        try:
            json_text = response.strip()
            start = json_text.find('[')
            end = json_text.rfind(']')
            if start != -1 and end != -1 and end > start:
                json_text = json_text[start:end+1]
            insights = json.loads(json_text)
            if isinstance(insights, list):
                return insights
        except Exception:
            pass

        # Fallback: build simple summaries
        fallback = []
        for job in top_jobs:
            fallback.append({
                "role": job.get("name"),
                "why_it_fits": f"Matches {len(job.get('matched_skills', []))} skills including "
                                f"{', '.join(job.get('matched_skills', [])[:3])}.",
                "skills_to_highlight": job.get("matched_skills", [])[:5],
                "gaps_to_address": job.get("missing_essential", [])[:5]
            })
        return fallback

    def translate_role_to_german(self, english_role: str) -> str:
        """Use Gemma to translate AI-generated job role to broader German job search terms"""
        prompt = f"""Convert this job role to BROAD German job search terms that work well with the German Arbeitsagentur job API.

CRITICAL RULES:
- Use BROAD terms that return many results, not specific compounds
- German job market uses broader categories than English
- If English role has multiple parts (&, and, /), pick PRIMARY skill only  
- Prefer common English terms or simple German categories over complex German compounds

SUCCESSFUL PATTERNS:
"Data Analyst" → "Analyst" (works great, returns 21+ jobs)
"Machine Learning Engineer" → "Developer" (broad technical term)
"Frontend Developer" → "Entwickler" (developer category) 
"Data Scientist" → "Analyst" (data analysis category)
"Software Engineer" → "Entwickler" (software development)
"Technical Product Manager" → "Manager" (management category)
"Research Scientist" → "Forscher" (research category)
"DevOps Engineer" → "Administrator" (systems category)
"UX Designer" → "Designer" (design category)
"Business Analyst" → "Analyst" (analysis category)

AVOID specific compounds like:
❌ "Datenanalyst" (returns 0 jobs)
❌ "Maschinenlernigeneur" (too specific)
❌ "Forschungsspezialist" (too narrow)

Job role to translate: "{english_role}"

Broad German search term:"""

        response = self._call_gemma(prompt)
        # Extract just the German translation, clean up any extra text
        german_role = response.strip()
        
        # Remove any quotes or extra explanation
        if german_role.startswith('"') and german_role.endswith('"'):
            german_role = german_role[1:-1]
        
        # Take only the first line if there's multiple lines
        german_role = german_role.split('\n')[0].strip()
        
        # Fallback to original if translation seems empty or invalid
        if not german_role or len(german_role) < 3:
            return english_role
            
        return german_role

    def suggest_job_cities(self, cv_text: str, skills: List[str], career_roles: List[str]) -> Dict[str, Any]:
        """Use Gemma to suggest 3 relevant German cities for job search based on CV analysis"""
        snippet = cv_text[:1500]
        top_skills = skills[:5] if skills else []
        top_roles = career_roles[:3] if career_roles else []
        
        prompt = f"""Analyze this CV to find the person's current city with confidence prioritization.

CV Text:
{snippet}

PRIORITY ORDER for detecting current city:
1. HIGHEST PRIORITY - Personal address mentioned in CV (city name in contact info/address)
2. HIGH PRIORITY - Most recent work experience with "present", "current", or latest end date + city
3. MEDIUM PRIORITY - Recent education institution + city (if work experience is old)
4. LOW PRIORITY - Any other city mentions

TASK: Scan the CV text for ANY German city names and determine WHY each city was mentioned. Then pick the most likely current city based on the priority order above.

German cities to detect: Berlin, München, Hamburg, Köln, Frankfurt, Stuttgart, Dresden, Leipzig, Hannover, Dortmund, Essen, Bremen, Nürnberg, Mannheim, Karlsruhe, Düsseldorf, Bonn, Wuppertal, Bielefeld, Münster

For each city found, analyze:
- Context: Why was this city mentioned? (address, work, education, etc.)
- Recency: How recent is the connection? (current, 2023, 2020, etc.)
- Confidence: How sure are you this is their current location?

After analysis, provide the best current city guess and 3 career opportunity cities.

Respond ONLY with JSON:
{{
  "detected_current": "most likely current city based on priority order, or null if no clear indication",
  "confidence": 0.0-1.0,
  "detection_reason": "brief explanation of why this city was chosen",
  "primary_city": "best city for career opportunities",
  "suggested_cities": [
    {{"city": "City1", "reason": "career opportunity reason"}},
    {{"city": "City2", "reason": "career opportunity reason"}}, 
    {{"city": "City3", "reason": "career opportunity reason"}}
  ]
}}"""

        response = self._call_gemma(prompt)
        try:
            parsed = json.loads(self._extract_json_object(response))
            return {
                "primary_city": (parsed.get("primary_city") or "").strip(),
                "suggested_cities": parsed.get("suggested_cities", []),
                "detected_current": (parsed.get("detected_current") or "").strip(),
                "confidence": parsed.get("confidence", 0.5),
                "detection_reason": (parsed.get("detection_reason") or "").strip()
            }
        except Exception:
            # Fallback: suggest major hubs based on skills
            fallback_cities = []
            skill_text = ' '.join(top_skills + top_roles).lower()
            
            if any(word in skill_text for word in ['software', 'tech', 'digital', 'ai', 'data']):
                fallback_cities.append({"city": "Berlin", "reason": "Major tech hub with many digital/software opportunities"})
                
            if any(word in skill_text for word in ['engineering', 'automotive', 'mechanical', 'manufacturing']):
                fallback_cities.append({"city": "München", "reason": "Engineering and automotive industry center"})
                
            if any(word in skill_text for word in ['finance', 'logistics', 'business', 'consulting']):
                fallback_cities.append({"city": "Frankfurt", "reason": "Financial and business services hub"})
                
            # Fill to 3 cities if needed
            default_cities = [
                {"city": "Hamburg", "reason": "Major business center with diverse opportunities"},
                {"city": "Köln", "reason": "Media and business hub"},
                {"city": "Stuttgart", "reason": "Technology and automotive center"}
            ]
            
            while len(fallback_cities) < 3:
                for city in default_cities:
                    if not any(c["city"] == city["city"] for c in fallback_cities):
                        fallback_cities.append(city)
                        if len(fallback_cities) >= 3:
                            break
                break
                            
            return {
                "primary_city": fallback_cities[0]["city"] if fallback_cities else "Berlin",
                "suggested_cities": fallback_cities[:3],
                "detected_current": "",
                "confidence": 0.3
            }

    def infer_location(self, cv_text: str) -> Dict[str, Any]:
        """Use Gemma to infer likely city/country from CV text"""
        snippet = cv_text[:1500]
        prompt = f"""Identify the most likely city (and country, if mentioned) associated with this CV.
Respond ONLY with JSON: {{"city":"...","country":"...","confidence":0-1,"evidence":"short quote"}}.
If no location is mentioned, set city to an empty string.

CV Text:
{snippet}
"""

        response = self._call_gemma(prompt)
        try:
            parsed = json.loads(self._extract_json_object(response))
            return {
                "city": (parsed.get("city") or "").strip(),
                "country": (parsed.get("country") or "").strip(),
                "confidence": parsed.get("confidence"),
                "evidence": parsed.get("evidence", "")
            }
        except Exception:
            import re
            match = re.search(r"\b(Berlin|Leipzig|München|Hamburg|Köln|Frankfurt|Stuttgart|Dresden|Bonn|Hannover)\b", cv_text, re.IGNORECASE)
            if match:
                return {
                    "city": match.group(0),
                    "country": "Deutschland",
                    "confidence": 0.4,
                    "evidence": "heuristic match"
                }
            return {}
