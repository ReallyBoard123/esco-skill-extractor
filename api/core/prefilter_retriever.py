"""Simple retrieval helper for Gemma prefilter"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer

class PrefilterRetriever:
    def __init__(self, data_path: Path, model_name: str = "BAAI/bge-m3"):
        self.data_path = data_path
        self.model_name = model_name
        self._examples: List[Dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._model = None
        self._load_examples()
        self._load_model()
        self._compute_embeddings()

    def _load_examples(self):
        if not self.data_path.exists():
            raise FileNotFoundError(f"Prefilter examples not found: {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as f:
            self._examples = json.load(f)
        if not isinstance(self._examples, list):
            raise ValueError("Prefilter examples must be a list")

    def _load_model(self):
        self._model = SentenceTransformer(self.model_name)

    def _compute_embeddings(self):
        texts = [item["text"] for item in self._examples]
        self._embeddings = self._model.encode(texts, normalize_embeddings=True)

    def get_examples_for_sentence(self, sentence: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not sentence.strip():
            return []
        query_emb = self._model.encode([sentence], normalize_embeddings=True)[0]
        similarities = np.dot(self._embeddings, query_emb)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = []
        for idx in top_indices:
            example = self._examples[idx].copy()
            example["similarity"] = float(similarities[idx])
            results.append(example)
        return results

    def majority_label(self, sentence: str, top_k: int = 3) -> str:
        examples = self.get_examples_for_sentence(sentence, top_k)
        if not examples:
            return "professional"
        label_scores = {}
        for ex in examples:
            label = ex.get("label", "professional")
            label_scores[label] = label_scores.get(label, 0) + ex.get("similarity", 0)
        return max(label_scores.items(), key=lambda item: item[1])[0]
