"""Clean ESCO Skill Extractor with rich data support"""

import csv
import os
import warnings
from typing import Dict, List, Optional

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

from .config import *


class ESCOExtractor:
    """Clean ESCO extractor with rich cross-referenced data"""
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        skills_threshold: float = DEFAULT_SKILLS_THRESHOLD,
        occupation_threshold: float = DEFAULT_OCCUPATIONS_THRESHOLD,
        device: str = None
    ):
        self.model_name = model
        self.skills_threshold = skills_threshold
        self.occupation_threshold = occupation_threshold
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # Core data
        self._skill_embeddings = None
        self._occupation_embeddings = None
        self._skill_labels = None
        self._occupation_labels = None
        self._skill_urls = None
        self._occupation_urls = None
        
        # Rich data
        self._skill_data = {}
        self._occupation_data = {}
        self._skill_categories = {}
        self._skill_relations = {}
        self._occupation_relations = {}
        
        # Initialize
        self._load_model()
        self._load_embeddings()
        self._load_rich_data()
    
    def _load_model(self):
        """Load SentenceTransformer model"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model = SentenceTransformer(self.model_name, device=self.device)
    
    def _load_embeddings(self):
        """Load pre-generated embeddings"""
        model_hash = get_model_hash(self.model_name)
        
        # Load skills
        skill_emb = DATA_DIR / f"skill_embeddings_{model_hash}_{DATA_VERSION}.bin"
        skill_labels = DATA_DIR / f"skill_labels_{model_hash}_{DATA_VERSION}.npy"
        skill_urls = DATA_DIR / f"skill_urls_{model_hash}_{DATA_VERSION}.npy"
        
        if not all(f.exists() for f in [skill_emb, skill_labels, skill_urls]):
            raise FileNotFoundError(
                f"Missing skill files. Run generate_clean_embeddings.py first."
            )
        
        self._skill_embeddings = torch.load(skill_emb, map_location=self.device, weights_only=False)
        self._skill_labels = np.load(skill_labels)
        self._skill_urls = np.load(skill_urls)
        
        # Load occupations  
        occ_emb = DATA_DIR / f"occupation_embeddings_{model_hash}_{DATA_VERSION}.bin"
        occ_labels = DATA_DIR / f"occupation_labels_{model_hash}_{DATA_VERSION}.npy"
        occ_urls = DATA_DIR / f"occupation_urls_{model_hash}_{DATA_VERSION}.npy"
        
        if not all(f.exists() for f in [occ_emb, occ_labels, occ_urls]):
            raise FileNotFoundError(
                f"Missing occupation files. Run generate_clean_embeddings.py first."
            )
        
        self._occupation_embeddings = torch.load(occ_emb, map_location=self.device, weights_only=False)
        self._occupation_labels = np.load(occ_labels)
        self._occupation_urls = np.load(occ_urls)
        
        print(f"✅ Loaded: {len(self._skill_labels)} skills, {len(self._occupation_labels)} occupations")
    
    def _load_rich_data(self):
        """Load cross-referenced ESCO data"""
        self._load_skill_data()
        self._load_occupation_data()
        self._load_categories()
        self._load_relations()
        print(f"✅ Rich data: {len(self._skill_data)} skills, {len(self._occupation_data)} occupations")
    
    def _load_skill_data(self):
        """Load skill records from CSV"""
        skills_file = ESCO_CSV_ROOT / "skills_en.csv"
        with open(skills_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uri = row['conceptUri']
                alt_labels = []
                if row['altLabels'] and row['altLabels'].strip():
                    alt_labels = [alt.strip() for alt in row['altLabels'].split('\n') if alt.strip()]
                
                self._skill_data[uri] = {
                    'name': row['preferredLabel'],
                    'uri': uri,
                    'type': row['skillType'],
                    'reuseLevel': row.get('reuseLevel', ''),
                    'description': row.get('description', ''),
                    'alternatives': alt_labels
                }
    
    def _load_occupation_data(self):
        """Load occupation records from CSV"""
        occ_file = ESCO_CSV_ROOT / "occupations_en.csv"
        with open(occ_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uri = row['conceptUri']
                alt_labels = []
                if row['altLabels'] and row['altLabels'].strip():
                    alt_labels = [alt.strip() for alt in row['altLabels'].split('\n') if alt.strip()]
                
                self._occupation_data[uri] = {
                    'name': row['preferredLabel'],
                    'uri': uri,
                    'iscoGroup': row.get('iscoGroup', ''),
                    'description': row.get('description', ''),
                    'alternatives': alt_labels
                }
    
    def _load_categories(self):
        """Load skill categories"""
        for category, filename in SKILL_CATEGORIES.items():
            file_path = ESCO_CSV_ROOT / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        uri = row['conceptUri']
                        if uri not in self._skill_categories:
                            self._skill_categories[uri] = []
                        self._skill_categories[uri].append(category)
    
    def _load_relations(self):
        """Load skill-occupation relationships"""
        relations_file = ESCO_CSV_ROOT / "occupationSkillRelations_en.csv"
        if relations_file.exists():
            with open(relations_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    occ_uri = row['occupationUri']
                    skill_uri = row['skillUri']
                    relation_type = row['relationType']
                    
                    # Skill -> occupations
                    if skill_uri not in self._skill_relations:
                        self._skill_relations[skill_uri] = {'used_in_jobs': []}
                    self._skill_relations[skill_uri]['used_in_jobs'].append({
                        'occupation_uri': occ_uri,
                        'relation_type': relation_type
                    })
                    
                    # Occupation -> skills
                    if occ_uri not in self._occupation_relations:
                        self._occupation_relations[occ_uri] = {'essential': [], 'optional': []}
                    self._occupation_relations[occ_uri][relation_type].append(skill_uri)
    
    def extract_skills(self, text: str, threshold: float = None, max_results: int = 10) -> List[Dict]:
        """Extract skills with similarity scores using tokenization strategy"""
        actual_threshold = threshold if threshold is not None else self.skills_threshold
        
        # Tokenize text into chunks for better skill matching
        tokens = self._tokenize_text(text)
        if not tokens:
            return []
        
        # Generate embeddings for all tokens
        token_embeddings = self._model.encode(
            tokens, device=self.device, normalize_embeddings=True, convert_to_tensor=True
        )
        
        # Calculate similarity matrix: tokens vs all skills
        similarities = util.dot_score(token_embeddings, self._skill_embeddings)
        
        # Find best matches across all tokens
        skill_matches = {}
        for token_idx, token_similarities in enumerate(similarities):
            valid_indices = torch.where(token_similarities > actual_threshold)[0]
            
            for skill_idx in valid_indices:
                skill_idx_item = skill_idx.item()
                similarity = token_similarities[skill_idx].item()
                
                # Keep the highest similarity for each skill
                if (skill_idx_item not in skill_matches or 
                    similarity > skill_matches[skill_idx_item]['similarity']):
                    skill_matches[skill_idx_item] = {
                        'name': self._skill_labels[skill_idx_item],
                        'uri': self._skill_urls[skill_idx_item],
                        'similarity': round(similarity, 3),
                        'matched_token': tokens[token_idx]
                    }
        
        # Sort by similarity and return top results
        sorted_matches = sorted(skill_matches.values(), key=lambda x: x['similarity'], reverse=True)
        return sorted_matches[:max_results]
    
    def extract_occupations(self, text: str, threshold: float = None, max_results: int = 10) -> List[Dict]:
        """Extract occupations with similarity scores using tokenization strategy"""
        actual_threshold = threshold if threshold is not None else self.occupation_threshold
        
        # Tokenize text into chunks for better occupation matching
        tokens = self._tokenize_text(text)
        if not tokens:
            return []
        
        # Generate embeddings for all tokens
        token_embeddings = self._model.encode(
            tokens, device=self.device, normalize_embeddings=True, convert_to_tensor=True
        )
        
        # Calculate similarity matrix: tokens vs all occupations
        similarities = util.dot_score(token_embeddings, self._occupation_embeddings)
        
        # Find best matches across all tokens
        occupation_matches = {}
        for token_idx, token_similarities in enumerate(similarities):
            valid_indices = torch.where(token_similarities > actual_threshold)[0]
            
            for occ_idx in valid_indices:
                occ_idx_item = occ_idx.item()
                similarity = token_similarities[occ_idx].item()
                
                # Keep the highest similarity for each occupation
                if (occ_idx_item not in occupation_matches or 
                    similarity > occupation_matches[occ_idx_item]['similarity']):
                    occupation_matches[occ_idx_item] = {
                        'name': self._occupation_labels[occ_idx_item],
                        'uri': self._occupation_urls[occ_idx_item], 
                        'similarity': round(similarity, 3),
                        'matched_token': tokens[token_idx]
                    }
        
        # Sort by similarity and return top results
        sorted_matches = sorted(occupation_matches.values(), key=lambda x: x['similarity'], reverse=True)
        return sorted_matches[:max_results]
    
    def _tokenize_text(self, text: str) -> List[str]:
        """
        Enhanced tokenization strategy for better skill/occupation matching.
        
        Improvements over original:
        - Better sentence boundary detection
        - Preserve multi-word technical terms
        - Filter out noise (URLs, emails, phone numbers)
        - Handle various text formats (CV, job descriptions)
        """
        import re
        
        if not text or not text.strip():
            return []
        
        # Clean the text first
        cleaned_text = self._clean_text(text)
        
        # Split on multiple delimiters but preserve meaningful chunks
        # Original: r"\r|\n|\t|\.|\,|\;|and|or"
        # Enhanced: Better handling of sentences, bullet points, lists
        tokens = []
        
        # First split by major structural elements
        sections = re.split(r'\n\s*\n|\r\n\s*\r\n', cleaned_text)  # Double newlines (paragraphs)
        
        for section in sections:
            # Split each section by sentence-ending punctuation, lists, etc.
            sentences = re.split(r'[.!?]+\s+|[\n\r]+\s*[-•*]\s*|[\n\r]+\s*\d+\.\s*', section)
            
            for sentence in sentences:
                if not sentence.strip():
                    continue
                    
                # Further split long sentences by commas, semicolons, connectors
                sub_chunks = re.split(r'[,;]\s+|\s+and\s+|\s+or\s+|\s*[|]\s*', sentence.strip())
                
                for chunk in sub_chunks:
                    chunk = chunk.strip()
                    if len(chunk) > 3 and self._is_meaningful_chunk(chunk):
                        tokens.append(chunk)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tokens = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                unique_tokens.append(token)
        
        return unique_tokens[:100]  # Limit to prevent too many embeddings
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for better processing"""
        import re
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove emails
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove phone numbers (basic patterns)
        text = re.sub(r'[\+]?[(]?[\d\s\-\(\)]{10,}', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove extra punctuation
        text = re.sub(r'[^\w\s\.,;:!?\-()&+/]', '', text)
        
        return text.strip()
    
    def _is_meaningful_chunk(self, chunk: str) -> bool:
        """Filter out noise and keep meaningful text chunks"""
        import re
        
        # Skip if too short or too long
        if len(chunk) < 3 or len(chunk) > 200:
            return False
            
        # Skip if mostly numbers or special characters
        if len(re.sub(r'[0-9\s\-().,]', '', chunk)) < 3:
            return False
            
        # Skip common noise patterns
        noise_patterns = [
            r'^\s*\d+\s*$',  # Just numbers
            r'^\s*[^\w]+\s*$',  # Just punctuation
            r'^\s*\w{1,2}\s*$',  # Single/double letters
            r'^\s*\d{1,4}[-/]\d{1,4}[-/]\d{2,4}\s*$',  # Dates
            r'^\s*page\s+\d+\s*$',  # Page numbers
        ]
        
        for pattern in noise_patterns:
            if re.match(pattern, chunk, re.IGNORECASE):
                return False
        
        return True
    
    def get_rich_skill_data(self, skill_uri: str, similarity: float = None) -> Dict:
        """Get comprehensive skill data"""
        if skill_uri not in self._skill_data:
            raise ValueError(f"Skill not found: {skill_uri}")
        
        data = self._skill_data[skill_uri].copy()
        data['categories'] = self._skill_categories.get(skill_uri, [])
        
        # Job usage
        relations = self._skill_relations.get(skill_uri, {})
        job_relations = relations.get('used_in_jobs', [])
        job_examples = [
            self._occupation_data[rel['occupation_uri']]['name']
            for rel in job_relations[:3]
            if rel['occupation_uri'] in self._occupation_data
        ]
        
        data['usedInOccupations'] = {
            'count': len(job_relations),
            'examples': job_examples,
            'breakdown': {
                'essential': len([r for r in job_relations if r['relation_type'] == 'essential']),
                'optional': len([r for r in job_relations if r['relation_type'] == 'optional'])
            }
        }
        
        if similarity is not None:
            data['similarity'] = round(similarity, 3)
        
        return data
    
    def get_rich_occupation_data(self, occ_uri: str, similarity: float = None) -> Dict:
        """Get comprehensive occupation data"""
        if occ_uri not in self._occupation_data:
            raise ValueError(f"Occupation not found: {occ_uri}")
        
        data = self._occupation_data[occ_uri].copy()
        relations = self._occupation_relations.get(occ_uri, {})
        
        # Required skills
        essential = [
            self._skill_data[uri]['name']
            for uri in relations.get('essential', [])
            if uri in self._skill_data
        ]
        optional = [
            self._skill_data[uri]['name']
            for uri in relations.get('optional', [])
            if uri in self._skill_data
        ]
        
        data['requiredSkills'] = {
            'essential': essential[:10],
            'optional': optional[:10],
            'totalEssential': len(essential),
            'totalOptional': len(optional)
        }
        
        # Skill categories
        all_skills = relations.get('essential', []) + relations.get('optional', [])
        category_counts = {}
        for skill_uri in all_skills:
            categories = self._skill_categories.get(skill_uri, ['general'])
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        data['skillCategories'] = category_counts
        
        if similarity is not None:
            data['similarity'] = round(similarity, 3)
        
        return data
    
    def get_category_summary(self) -> Dict:
        """Get skill category summary"""
        category_counts = {}
        for categories in self._skill_categories.values():
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            'categories': category_counts,
            'totalSkillsWithCategories': len(self._skill_categories),
            'totalSkills': len(self._skill_data)
        }