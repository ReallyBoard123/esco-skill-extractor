"""Configuration for ESCO API"""

from pathlib import Path

# Paths
API_ROOT = Path(__file__).parent.parent
DATA_DIR = API_ROOT / "data"
ESCO_CSV_ROOT = API_ROOT.parent / "ESCO dataset - v1.2.0 - classification - en - csv"

# Settings
DEFAULT_MODEL = "BAAI/bge-m3"
DATA_VERSION = "v1.2.0"
DEFAULT_SKILLS_THRESHOLD = 0.6
DEFAULT_OCCUPATIONS_THRESHOLD = 0.55

# Category files
SKILL_CATEGORIES = {
    'digital': 'digitalSkillsCollection_en.csv',
    'green': 'greenSkillsCollection_en.csv', 
    'transversal': 'transversalSkillsCollection_en.csv',
    'language': 'languageSkillsCollection_en.csv',
    'research': 'researchSkillsCollection_en.csv',
    'digComp': 'digCompSkillsCollection_en.csv'
}

# API info
API_INFO = {
    "title": "ESCO Skill Extractor API",
    "description": "Extract ESCO skills and occupations with rich cross-referenced data using BGE-M3 embeddings",
    "version": "2.0.0",
    "features": [
        "ESCO v1.2.0 official data",
        "BGE-M3 1024D embeddings", 
        "Rich cross-referenced data",
        "Skill categorization",
        "Occupation-skill relationships",
        "PDF processing support"
    ]
}

def get_model_hash(model_name: str) -> str:
    """Get model hash for cache files"""
    import hashlib
    return hashlib.md5(model_name.encode()).hexdigest()[:8]