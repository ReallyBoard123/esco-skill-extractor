#!/usr/bin/env python3
"""
Generate BGE-M3 embeddings from official ESCO v1.2.0 CSV data
"""

import pandas as pd
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
import hashlib
import os
from pathlib import Path
import time
from tqdm import tqdm

def main():
    print("🚀 Generating clean ESCO embeddings with BGE-M3...")
    
    # Initialize model
    model_name = "BAAI/bge-m3"
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    # Auto-detect device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Paths - using official ESCO v1.2.0 data
    skills_file = Path("ESCO dataset - v1.2.0 - classification - en - csv/skills_en.csv")
    occupations_file = Path("ESCO dataset - v1.2.0 - classification - en - csv/occupations_en.csv")
    
    # Output paths - updated for clean structure
    data_dir = Path("api/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate model hash for cache filenames
    model_hash = hashlib.md5(model_name.encode()).hexdigest()[:8]
    print(f"Model hash: {model_hash}")
    
    # Process skills
    print("📋 Loading skills CSV...")
    skills_df = pd.read_csv(skills_file)
    print(f"Loaded {len(skills_df)} skills")
    
    print("🧠 Generating skill embeddings...")
    # Combine preferredLabel with altLabels for better matching
    skill_texts = []
    skill_labels = []
    skill_urls = []
    
    for _, row in skills_df.iterrows():
        preferred = row['preferredLabel'].strip()
        if not preferred:  # Skip rows without preferredLabel
            continue
            
        # Parse alternative labels (newline-separated)
        alt_labels = []
        if pd.notna(row['altLabels']) and row['altLabels'].strip():
            alt_labels = [alt.strip() for alt in row['altLabels'].split('\n') if alt.strip()]
        
        # Create combined text: preferred label + alternatives for embedding
        combined_text = preferred
        if alt_labels:
            # Include top 3 alternatives to avoid too long text
            combined_text += " | " + " | ".join(alt_labels[:3])
        
        skill_texts.append(combined_text)
        skill_labels.append(preferred)  # Keep clean preferred label for display
        skill_urls.append(row['conceptUri'])
    
    print(f"Processing {len(skill_texts)} skills with combined text...")
    
    # Generate embeddings from combined text (preferred + alternatives)
    start_time = time.time()
    skill_embeddings = model.encode(
        skill_texts,
        device=device,
        normalize_embeddings=True,
        convert_to_tensor=True,
        show_progress_bar=True,
        batch_size=64 if device == "cuda" else 32
    )
    skills_time = time.time() - start_time
    print(f"⏱️ Skills embeddings generated in {skills_time:.1f}s")
    
    # Save skills embeddings and metadata
    skills_cache_file = data_dir / f"skill_embeddings_{model_hash}_v1.2.0.bin"
    torch.save(skill_embeddings, skills_cache_file)
    print(f"✅ Skills embeddings saved: {skills_cache_file}")
    
    # Save URLs and labels for matching
    skills_urls_file = data_dir / f"skill_urls_{model_hash}_v1.2.0.npy"
    skills_labels_file = data_dir / f"skill_labels_{model_hash}_v1.2.0.npy"
    np.save(skills_urls_file, skill_urls)
    np.save(skills_labels_file, skill_labels)
    print(f"✅ Skills URLs and labels saved: {skills_urls_file.name}, {skills_labels_file.name}")
    
    # Process occupations
    print("🏢 Loading occupations CSV...")
    occupations_df = pd.read_csv(occupations_file)
    print(f"Loaded {len(occupations_df)} occupations")
    
    print("🧠 Generating occupation embeddings...")
    # Combine preferredLabel with altLabels for better matching
    occupation_texts = []
    occupation_labels = []
    occupation_urls = []
    
    for _, row in occupations_df.iterrows():
        preferred = row['preferredLabel'].strip()
        if not preferred:  # Skip rows without preferredLabel
            continue
            
        # Parse alternative labels (newline-separated)
        alt_labels = []
        if pd.notna(row['altLabels']) and row['altLabels'].strip():
            alt_labels = [alt.strip() for alt in row['altLabels'].split('\n') if alt.strip()]
        
        # Create combined text: preferred label + alternatives for embedding
        combined_text = preferred
        if alt_labels:
            # Include top 3 alternatives to avoid too long text
            combined_text += " | " + " | ".join(alt_labels[:3])
        
        occupation_texts.append(combined_text)
        occupation_labels.append(preferred)  # Keep clean preferred label for display
        occupation_urls.append(row['conceptUri'])
    
    print(f"Processing {len(occupation_texts)} occupations with combined text...")
    
    # Generate embeddings from combined text (preferred + alternatives)
    start_time = time.time()
    occupation_embeddings = model.encode(
        occupation_texts,
        device=device,
        normalize_embeddings=True,
        convert_to_tensor=True,
        show_progress_bar=True,
        batch_size=64 if device == "cuda" else 32
    )
    occupations_time = time.time() - start_time
    print(f"⏱️ Occupations embeddings generated in {occupations_time:.1f}s")
    
    # Save occupations embeddings and metadata
    occupations_cache_file = data_dir / f"occupation_embeddings_{model_hash}_v1.2.0.bin"
    torch.save(occupation_embeddings, occupations_cache_file)
    print(f"✅ Occupation embeddings saved: {occupations_cache_file}")
    
    # Save URLs and labels for matching
    occupation_urls_file = data_dir / f"occupation_urls_{model_hash}_v1.2.0.npy"
    occupation_labels_file = data_dir / f"occupation_labels_{model_hash}_v1.2.0.npy"
    np.save(occupation_urls_file, occupation_urls)
    np.save(occupation_labels_file, occupation_labels)
    print(f"✅ Occupation URLs and labels saved: {occupation_urls_file.name}, {occupation_labels_file.name}")
    
    total_time = skills_time + occupations_time
    print("\n🎉 Clean embeddings generation complete!")
    print(f"📊 Skills: {len(skill_texts)} valid items, {skill_embeddings.shape[1]}D embeddings")
    print(f"📊 Occupations: {len(occupation_texts)} valid items, {occupation_embeddings.shape[1]}D embeddings")
    print(f"⏱️ Total processing time: {total_time:.1f}s")
    print(f"💾 Cache files use model hash: {model_hash}")
    
    # Test a sample
    print("\n🔍 Testing sample skill matches...")
    test_queries = ["python programming", "team management", "data analysis"]
    
    for test_query in test_queries:
        test_embedding = model.encode([test_query], normalize_embeddings=True, convert_to_tensor=True)
        similarities = torch.cosine_similarity(test_embedding, skill_embeddings)
        top_indices = torch.topk(similarities, 3).indices.cpu().numpy()
        
        print(f"\nQuery: '{test_query}'")
        for i, idx in enumerate(top_indices):
            score = similarities[idx].item()
            skill_name = skill_labels[idx]
            print(f"  {i+1}. {skill_name} (score: {score:.3f})")

if __name__ == "__main__":
    main()