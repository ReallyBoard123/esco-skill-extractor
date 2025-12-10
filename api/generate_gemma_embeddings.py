#!/usr/bin/env python3
"""
Generate EmbeddingGemma embeddings for ESCO dataset
Compares with existing BGE-M3 embeddings and creates versioned cache files
"""

import csv
import hashlib
import json
import numpy as np
import ollama
import os
import pandas as pd
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import torch

class EmbeddingGemmaGenerator:
    def __init__(self, data_dir: str = "api/data", batch_size: int = 50):
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        self.client = ollama.Client()
        self.model_name = "embeddinggemma"
        
        # Generate model hash for cache versioning
        self.model_hash = hashlib.md5(self.model_name.encode()).hexdigest()[:8]
        
        print(f"🚀 Initializing EmbeddingGemma Generator")
        print(f"📁 Data directory: {self.data_dir}")
        print(f"🔢 Model hash: {self.model_hash}")
        print(f"📦 Batch size: {batch_size}")
        
    def test_ollama_connection(self) -> bool:
        """Test if Ollama is running and EmbeddingGemma is available"""
        try:
            # Test with a simple embedding
            response = self.client.embeddings(
                model=self.model_name,
                prompt="test embedding"
            )
            embedding = response['embedding']
            print(f"✅ Ollama connection successful")
            print(f"📏 Embedding dimension: {len(embedding)}")
            return True
            
        except Exception as e:
            print(f"❌ Ollama connection failed: {e}")
            print(f"💡 Make sure Ollama is running and EmbeddingGemma is installed:")
            print(f"   ollama pull embeddinggemma")
            return False
    
    def load_esco_data(self) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str]]:
        """Load ESCO skills and occupations data"""
        print("📖 Loading ESCO dataset...")
        
        # Load skills data
        skills_file = self.data_dir.parent / "ESCO dataset - v1.2.0 - classification - en - csv" / "skills_en.csv"
        occupations_file = self.data_dir.parent / "ESCO dataset - v1.2.0 - classification - en - csv" / "occupations_en.csv"
        
        if not skills_file.exists():
            raise FileNotFoundError(f"Skills file not found: {skills_file}")
        if not occupations_file.exists():
            raise FileNotFoundError(f"Occupations file not found: {occupations_file}")
        
        # Process skills
        skill_texts = []
        skill_labels = []
        skill_urls = []
        
        with open(skills_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                preferred_label = row['preferredLabel'].strip()
                if preferred_label:
                    # Create ENHANCED text for embedding (beyond BGE-M3)
                    alt_labels = []
                    if row['altLabels'] and row['altLabels'].strip():
                        alt_labels = [alt.strip() for alt in row['altLabels'].split('\n') if alt.strip()]
                    
                    # Enhanced context for better EmbeddingGemma understanding
                    context_parts = [preferred_label]
                    
                    # Add skill type context
                    if row.get('skillType'):
                        context_parts.append(f"Type: {row['skillType']}")
                    
                    # Add reuse level context  
                    if row.get('reuseLevel'):
                        context_parts.append(f"Level: {row['reuseLevel']}")
                    
                    # Add description context (first 100 chars for context)
                    if row.get('description') and row['description'].strip():
                        desc = row['description'].strip()[:100]
                        context_parts.append(f"Description: {desc}")
                    
                    # Add top 3 alternatives
                    if alt_labels:
                        context_parts.extend(alt_labels[:3])
                    
                    text_for_embedding = " | ".join(context_parts)
                    
                    skill_texts.append(text_for_embedding)
                    skill_labels.append(preferred_label)  # Clean label for display
                    skill_urls.append(row['conceptUri'])
        
        # Process occupations
        occupation_texts = []
        occupation_labels = []
        occupation_urls = []
        
        with open(occupations_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                preferred_label = row['preferredLabel'].strip()
                if preferred_label:
                    # Create rich text for embedding
                    alt_labels = []
                    if row['altLabels'] and row['altLabels'].strip():
                        alt_labels = [alt.strip() for alt in row['altLabels'].split('\n') if alt.strip()]
                    
                    text_for_embedding = preferred_label
                    if alt_labels:
                        text_for_embedding += " | " + " | ".join(alt_labels[:3])
                    
                    occupation_texts.append(text_for_embedding)
                    occupation_labels.append(preferred_label)
                    occupation_urls.append(row['conceptUri'])
        
        print(f"✅ Loaded {len(skill_texts)} skills and {len(occupation_texts)} occupations")
        return skill_texts, skill_labels, skill_urls, occupation_texts, occupation_labels, occupation_urls
    
    def generate_embeddings_batch(self, texts: List[str], description: str = "") -> np.ndarray:
        """Generate embeddings in batches with progress tracking"""
        print(f"🔄 Generating {description} embeddings for {len(texts)} items...")
        
        all_embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
        
        start_time = time.time()
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} items)...")
            
            batch_embeddings = []
            for text in batch:
                try:
                    response = self.client.embeddings(
                        model=self.model_name,
                        prompt=text
                    )
                    embedding = response['embedding']
                    batch_embeddings.append(embedding)
                    
                except Exception as e:
                    print(f"⚠️  Error generating embedding for text: {text[:50]}...")
                    print(f"   Error: {e}")
                    # Use zero vector as fallback
                    batch_embeddings.append([0.0] * 768)  # EmbeddingGemma default dimension
            
            all_embeddings.extend(batch_embeddings)
            
            # Progress update
            elapsed = time.time() - start_time
            items_processed = min(i + self.batch_size, len(texts))
            rate = items_processed / elapsed if elapsed > 0 else 0
            remaining = len(texts) - items_processed
            eta = remaining / rate if rate > 0 else 0
            
            print(f"   ⏱️  Rate: {rate:.1f} items/sec, ETA: {eta:.0f}s")
        
        embeddings_array = np.array(all_embeddings, dtype=np.float32)
        total_time = time.time() - start_time
        
        print(f"✅ {description} embeddings complete!")
        print(f"   📏 Shape: {embeddings_array.shape}")
        print(f"   ⏱️  Total time: {total_time:.1f}s")
        print(f"   🚀 Average rate: {len(texts) / total_time:.1f} items/sec")
        
        return embeddings_array
    
    def save_embeddings_cache(self, 
                            skill_embeddings: np.ndarray, 
                            skill_labels: List[str],
                            skill_urls: List[str],
                            occupation_embeddings: np.ndarray,
                            occupation_labels: List[str],
                            occupation_urls: List[str]):
        """Save embeddings to versioned cache files"""
        print("💾 Saving EmbeddingGemma cache files...")
        
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Save embeddings (binary format for efficiency)
        skill_embeddings_file = self.data_dir / f"skill_embeddings_{self.model_hash}_v1.2.0_gemma.bin"
        occupation_embeddings_file = self.data_dir / f"occupation_embeddings_{self.model_hash}_v1.2.0_gemma.bin"
        
        torch.save(torch.from_numpy(skill_embeddings), skill_embeddings_file)
        torch.save(torch.from_numpy(occupation_embeddings), occupation_embeddings_file)
        
        # Save labels (numpy format)
        skill_labels_file = self.data_dir / f"skill_labels_{self.model_hash}_v1.2.0_gemma.npy"
        occupation_labels_file = self.data_dir / f"occupation_labels_{self.model_hash}_v1.2.0_gemma.npy"
        
        np.save(skill_labels_file, np.array(skill_labels))
        np.save(occupation_labels_file, np.array(occupation_labels))
        
        # Save URLs
        skill_urls_file = self.data_dir / f"skill_urls_{self.model_hash}_v1.2.0_gemma.npy"
        occupation_urls_file = self.data_dir / f"occupation_urls_{self.model_hash}_v1.2.0_gemma.npy"
        
        np.save(skill_urls_file, np.array(skill_urls))
        np.save(occupation_urls_file, np.array(occupation_urls))
        
        # Save metadata
        metadata = {
            "model": self.model_name,
            "model_hash": self.model_hash,
            "esco_version": "v1.2.0",
            "embedding_dimension": skill_embeddings.shape[1],
            "skills_count": len(skill_labels),
            "occupations_count": len(occupation_labels),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "files": {
                "skill_embeddings": str(skill_embeddings_file.name),
                "occupation_embeddings": str(occupation_embeddings_file.name),
                "skill_labels": str(skill_labels_file.name),
                "occupation_labels": str(occupation_labels_file.name),
                "skill_urls": str(skill_urls_file.name),
                "occupation_urls": str(occupation_urls_file.name)
            }
        }
        
        metadata_file = self.data_dir / f"metadata_{self.model_hash}_v1.2.0_gemma.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Calculate file sizes
        total_size = sum([
            skill_embeddings_file.stat().st_size,
            occupation_embeddings_file.stat().st_size,
            skill_labels_file.stat().st_size,
            occupation_labels_file.stat().st_size,
            skill_urls_file.stat().st_size,
            occupation_urls_file.stat().st_size
        ])
        
        print(f"✅ Cache files saved!")
        print(f"   📁 Directory: {self.data_dir}")
        print(f"   📊 Total size: {total_size / (1024*1024):.1f} MB")
        print(f"   🔧 Model hash: {self.model_hash}")
        print(f"   📋 Metadata: {metadata_file.name}")
        
        return metadata_file
    
    def compare_with_bge_m3(self):
        """Compare EmbeddingGemma cache with existing BGE-M3 cache"""
        print("🔍 Comparing with existing BGE-M3 embeddings...")
        
        # Look for BGE-M3 cache files (hash: 75e678d2)
        bge_skill_file = self.data_dir / "skill_embeddings_75e678d2_v1.2.0.bin"
        bge_occupation_file = self.data_dir / "occupation_embeddings_75e678d2_v1.2.0.bin"
        
        gemma_skill_file = self.data_dir / f"skill_embeddings_{self.model_hash}_v1.2.0_gemma.bin"
        gemma_occupation_file = self.data_dir / f"occupation_embeddings_{self.model_hash}_v1.2.0_gemma.bin"
        
        if bge_skill_file.exists() and gemma_skill_file.exists():
            bge_size = bge_skill_file.stat().st_size + bge_occupation_file.stat().st_size
            gemma_size = gemma_skill_file.stat().st_size + gemma_occupation_file.stat().st_size
            
            print(f"📊 Size Comparison:")
            print(f"   BGE-M3 (1024D):     {bge_size / (1024*1024):.1f} MB")
            print(f"   EmbeddingGemma (768D): {gemma_size / (1024*1024):.1f} MB")
            print(f"   Size reduction:     {((bge_size - gemma_size) / bge_size * 100):.1f}%")
            
            # Load both embeddings for dimension comparison
            bge_embeddings = torch.load(bge_skill_file, map_location='cpu')
            gemma_embeddings = torch.load(gemma_skill_file, map_location='cpu')
            
            print(f"📏 Dimension Comparison:")
            print(f"   BGE-M3:        {bge_embeddings.shape}")
            print(f"   EmbeddingGemma: {gemma_embeddings.shape}")
        else:
            print("⚠️  BGE-M3 embeddings not found for comparison")

def main():
    """Generate EmbeddingGemma embeddings for ESCO dataset"""
    print("🚀 EmbeddingGemma ESCO Embedding Generator")
    print("=" * 50)
    
    generator = EmbeddingGemmaGenerator()
    
    # Test Ollama connection
    if not generator.test_ollama_connection():
        print("❌ Cannot proceed without Ollama connection")
        return
    
    try:
        # Load ESCO data
        skill_texts, skill_labels, skill_urls, occupation_texts, occupation_labels, occupation_urls = generator.load_esco_data()
        
        # Generate skill embeddings
        skill_embeddings = generator.generate_embeddings_batch(
            skill_texts, 
            f"skill ({len(skill_texts)} items)"
        )
        
        # Generate occupation embeddings
        occupation_embeddings = generator.generate_embeddings_batch(
            occupation_texts,
            f"occupation ({len(occupation_texts)} items)"
        )
        
        # Save to cache files
        metadata_file = generator.save_embeddings_cache(
            skill_embeddings, skill_labels, skill_urls,
            occupation_embeddings, occupation_labels, occupation_urls
        )
        
        # Compare with BGE-M3
        generator.compare_with_bge_m3()
        
        print("\n✅ EmbeddingGemma embedding generation complete!")
        print(f"📋 Metadata saved to: {metadata_file}")
        
    except Exception as e:
        print(f"❌ Error during embedding generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()