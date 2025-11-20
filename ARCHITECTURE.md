# ESCO Skill Extractor - Project Architecture Guide

## Overview
The ESCO Skill Extractor is a full-stack application that extracts ESCO skills and ISCO occupations from text using sentence transformer models and semantic similarity.

## Project Structure

```
esco-skill-extractor/
├── api/                          # Backend (Python FastAPI)
│   ├── esco_skill_extractor/
│   │   ├── __init__.py          # Core SkillExtractor class
│   │   ├── __main__.py          # CLI entry point and server startup
│   │   ├── api.py               # FastAPI routes and middleware
│   │   ├── models.py            # Pydantic models for API validation
│   │   └── data/                # ESCO data and cached embeddings
│   │       ├── skills.csv       # 13,939 ESCO skills
│   │       ├── occupations.csv  # 3,658 ISCO occupations
│   │       ├── skill_embeddings.bin      # Cached skill embeddings
│   │       └── occupation_embeddings.bin # Cached occupation embeddings
│   ├── requirements.txt         # Python dependencies
│   └── setup.py                # Package setup
└── app/                         # Frontend (Next.js)
    ├── app/
    │   ├── api/                 # Next.js API routes
    │   │   ├── decode-esco/     # ESCO URL decoding
    │   │   └── extract-pdf-text/ # PDF text extraction
    │   ├── layout.tsx           # Root layout
    │   └── page.tsx             # Main application page
    ├── components/              # React components
    ├── package.json             # Node dependencies
    └── pnpm-lock.yaml          # Package manager lock file
```

## Backend Architecture

### Core Components

#### 1. SkillExtractor Class (`__init__.py`)
- **Purpose**: Main engine for skill/occupation extraction
- **Key Methods**:
  - `get_skills(texts)`: Extract ESCO skills from input texts
  - `get_occupations(texts)`: Extract ISCO occupations from input texts
  - `remove_embeddings()`: Clear cached embeddings (use when switching models)

#### 2. FastAPI Server (`api.py`)
- **Purpose**: REST API endpoints and CORS configuration
- **Endpoints**:
  - `GET /health`: Health check with model info
  - `POST /extract-skills`: Extract skills from texts
  - `POST /extract-occupations`: Extract occupations from texts
  - Legacy endpoints for backward compatibility

#### 3. CLI Interface (`__main__.py`)
- **Purpose**: Command-line server startup with configurable options
- **Key Parameters**:
  - `--model`: Sentence transformer model to use
  - `--skill_threshold`: Similarity threshold for skills (default: 0.6)
  - `--occupation_threshold`: Similarity threshold for occupations (default: 0.55)
  - `--host/--port`: Server configuration

### How It Works

1. **Initialization**:
   - Load specified sentence transformer model
   - Load ESCO skills/occupations from CSV files
   - Generate or load cached embeddings

2. **Embedding Generation**:
   - Skills: 13,939 descriptions → 384-dim embeddings
   - Occupations: 3,658 descriptions → 384-dim embeddings
   - Cache to `.bin` files for faster subsequent loads

3. **Extraction Process**:
   - Encode input text using sentence transformer
   - Calculate cosine similarity with all cached embeddings
   - Return URLs above threshold, sorted by similarity

## Frontend Architecture

### Technology Stack
- **Framework**: Next.js 16 with React 19
- **Package Manager**: pnpm
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI + Custom components

### Key Features
- PDF text extraction via `/api/extract-pdf-text`
- ESCO URL decoding via `/api/decode-esco`
- Real-time skill/occupation extraction
- Responsive design with modern UI

## Model Switching Guide

### Issue: Empty Results After Model Change
When switching sentence transformer models (e.g., from `all-MiniLM-L6-v2` to `BAAI/bge-small-en-v1.5`), you may get empty results due to embedding space incompatibility.

### Root Cause
- Different models create different embedding spaces
- Cached embeddings from old model become incompatible
- Similarity calculations fail, returning no matches

### Solution Steps

1. **Stop the server**:
   ```bash
   pkill -f "python -m esco_skill_extractor"
   ```

2. **Clear cached embeddings** (one of these methods):
   ```bash
   # Method 1: Delete manually
   rm api/esco_skill_extractor/data/*_embeddings.bin
   
   # Method 2: Use built-in method
   python -c "from esco_skill_extractor import SkillExtractor; SkillExtractor.remove_embeddings()"
   ```

3. **Restart with new model**:
   ```bash
   cd api
   python -m esco_skill_extractor --model "BAAI/bge-small-en-v1.5"
   ```

4. **Wait for embedding generation**:
   - First startup will take longer (generating 17K+ embeddings)
   - Subsequent startups will be fast (loading cached embeddings)

### Supported Models
Any sentence-transformers compatible model that outputs 384-dimensional embeddings, including:
- `all-MiniLM-L6-v2` (default original)
- `BAAI/bge-small-en-v1.5` (new default)
- `sentence-transformers/all-mpnet-base-v2`
- Custom fine-tuned models

## Development Workflow

### Starting the Application

1. **Backend**:
   ```bash
   cd api
   python -m esco_skill_extractor --host 0.0.0.0 --port 8000
   ```

2. **Frontend**:
   ```bash
   cd app
   pnpm dev
   ```

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Extract skills
curl -X POST http://localhost:8000/extract-skills \
  -H "Content-Type: application/json" \
  -d '{"texts": ["I am a software engineer with Python experience"]}'
```

### Performance Considerations

- **First run**: Embedding generation takes 5-10 minutes
- **Subsequent runs**: Fast startup using cached embeddings
- **Memory usage**: ~500MB for model + embeddings
- **API response time**: 100-500ms per request

## Troubleshooting

### Common Issues

1. **Empty results**: Clear embeddings and restart (see Model Switching Guide)
2. **CUDA warnings**: Normal on CPU-only systems, doesn't affect functionality
3. **Server won't start**: Check port availability (default 8000)
4. **Frontend build errors**: Ensure pnpm is used, not npm

### Debug Commands

```bash
# Check if server is running
curl http://localhost:8000/health

# View server logs
python -m esco_skill_extractor --host localhost

# Check embedding files
ls -la api/esco_skill_extractor/data/*.bin
```