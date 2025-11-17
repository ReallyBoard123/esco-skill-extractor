from itertools import chain
from typing import Union, List
import warnings
import os
import re
import hashlib

from sentence_transformers import SentenceTransformer, util

import pandas as pd
import numpy as np
import torch


class SkillExtractor:
    _dir = __file__.replace("__init__.py", "")

    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
        skills_threshold: float = 0.63,
        occupation_threshold: float = 0.60,
        device: Union[str, None] = None,
    ):
        """
        Loads the models, skills and skill embeddings.

        Args:
            skills_threshold (float, optional): The similarity threshold for skill comparisons. Increase it to be more harsh. Defaults to 0.45. Range: [0, 1].
            occupation_threshold (float, optional): The similarity threshold for occupation comparisons. Increase it to be more harsh. Defaults to 0.55. Range: [0, 1].
            device (Union[str, None], optional): The device where the model will run. Defaults to "cuda" if available, otherwise "cpu".
        """

        self.model_name = model
        self.skills_threshold = skills_threshold
        self.occupation_threshold = occupation_threshold
        self.device = (
            device if device else "cuda" if torch.cuda.is_available() else "cpu"
        )
        self._load_models()
        self._load_skills()
        self._load_occupations()
        self._check_cache_compatibility()
        self._create_skill_embeddings()
        self._create_occupation_embeddings()

    def _get_cache_filename(self, entity_type: str) -> str:
        """
        Generate cache filename with model hash for version safety.
        
        Args:
            entity_type: Either 'skill' or 'occupation'
            
        Returns:
            str: Versioned cache filename
        """
        model_hash = hashlib.md5(self.model_name.encode()).hexdigest()[:8]
        return f"{SkillExtractor._dir}/data/{entity_type}_embeddings_{model_hash}.bin"

    def _check_cache_compatibility(self):
        """
        Check for legacy cache files and warn about model/cache mismatches.
        """
        data_dir = f"{SkillExtractor._dir}/data/"
        
        # Check for old unversioned cache files
        old_skill_cache = f"{data_dir}skill_embeddings.bin"
        old_occupation_cache = f"{data_dir}occupation_embeddings.bin"
        
        if os.path.exists(old_skill_cache) or os.path.exists(old_occupation_cache):
            print("WARNING: Found legacy cache files without model versioning!")
            print(f"Model: {self.model_name}")
            print("Legacy files will be ignored to prevent incompatibility issues.")
            print("New versioned cache files will be generated automatically.")
            print()
        
        # Check for other model cache files in directory
        current_hash = hashlib.md5(self.model_name.encode()).hexdigest()[:8]
        other_models = []
        
        for file in os.listdir(data_dir):
            if file.startswith(("skill_embeddings_", "occupation_embeddings_")) and file.endswith(".bin"):
                # Extract hash from filename
                parts = file.split("_")
                if len(parts) >= 3:
                    file_hash = parts[2].replace(".bin", "")
                    if file_hash != current_hash:
                        # Try to reverse engineer model name (this is informational only)
                        other_models.append(file_hash)
        
        if other_models:
            unique_hashes = list(set(other_models))
            print(f"Found cached embeddings for {len(unique_hashes)} other model(s)")
            print(f"Using cache for current model: {self.model_name} ({current_hash})")
            print()

    def _load_models(self):
        """
        This method loads the model from the SentenceTransformer library.
        """

        # Ignore the security warning messages about loading the model from pickle
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._model = SentenceTransformer(self.model_name, device=self.device)

    def _load_skills(self):
        """
        This method loads the skills from the skills.csv file.
        """

        self._skills = pd.read_csv(f"{SkillExtractor._dir}/data/skills.csv")
        self._skill_ids = self._skills["id"].to_numpy()

    def _load_occupations(self):
        """
        This method loads the occupations from the occupations.csv file.
        """

        self._occupations = pd.read_csv(f"{SkillExtractor._dir}/data/occupations.csv")
        self._occupation_ids = self._occupations["id"].to_numpy()

    def _create_skill_embeddings(self):
        """
        This method creates the skill embeddings and saves them to a cache file.
        If the cache file exists, it loads the embeddings from it.
        """
        cache_file = self._get_cache_filename("skill")
        
        if os.path.exists(cache_file):
            # Load embeddings with proper device mapping
            self._skill_embeddings = torch.load(cache_file, map_location=self.device, weights_only=False)
        else:
            print(f"Generating skill embeddings for model: {self.model_name}")
            print(f"Processing {len(self._skills)} skills...")
            self._skill_embeddings = self._model.encode(
                self._skills["description"].to_list(),
                device=self.device,
                normalize_embeddings=True,
                convert_to_tensor=True,
                show_progress_bar=True
            )
            torch.save(self._skill_embeddings, cache_file)
            print(f"Skill embeddings saved to: {os.path.basename(cache_file)}")

    def _create_occupation_embeddings(self):
        """
        This method creates the occupations embeddings and saves them to a cache file.
        If the cache file exists, it loads the embeddings from it.
        """
        cache_file = self._get_cache_filename("occupation")
        
        if os.path.exists(cache_file):
            # Load embeddings with proper device mapping
            self._occupation_embeddings = torch.load(cache_file, map_location=self.device, weights_only=False)
        else:
            print(f"Generating occupation embeddings for model: {self.model_name}")
            print(f"Processing {len(self._occupations)} occupations...")
            self._occupation_embeddings = self._model.encode(
                self._occupations["description"].to_list(),
                device=self.device,
                normalize_embeddings=True,
                convert_to_tensor=True,
                show_progress_bar=True
            )
            torch.save(self._occupation_embeddings, cache_file)
            print(f"Occupation embeddings saved to: {os.path.basename(cache_file)}")

    def _texts_to_tokens(self, texts: List[str]) -> List[List[str]]:
        """
        This method splits the texts into tokens.

        Args:
            texts (List[str]): The texts to be split.

        Returns:
            List[str]: A list of lists containing the tokens for each text.
        """

        return [
            [s for s in re.split(r"\r|\n|\t|\.|\,|\;|and|or", text.strip()) if s]
            for text in texts
        ]

    def _get_entity(
        self,
        texts: List[str],
        entity_ids: np.ndarray[str],
        entity_embeddings: torch.Tensor,
        threshold: float,
    ) -> List[List[str]]:
        """
        This method extracts the entities from the texts.

        Args:
            texts (List[str]): The texts from which the entities will be extracted.
            entity_ids (np.ndarray[str]): The IDs of the entities.
            entity_embeddings (torch.Tensor): The embeddings of the entities.
            threshold (float): The similarity threshold for entity comparisons. Increase it to be more harsh.

        Returns:
            List[List[str]]: A list of lists containing the IDs of the entities for each text.
        """

        # If there are no texts, return an empty list
        if all(not text for text in texts):
            return [[] for _ in texts]

        # Split the texts into tokens and then flatten them to perform calculations faster
        texts = self._texts_to_tokens(texts)
        tokens = list(chain.from_iterable(texts))

        # If there are no tokens, return an empty list
        if not tokens:
            return [[] for _ in texts]

        # Calculate the embeddings for all flattened tokens
        sentence_embeddings = self._model.encode(
            tokens,
            device=self.device,
            normalize_embeddings=True,
            convert_to_tensor=True,
        )

        # Calculate the similarity between all flattened tokens and all entities and
        # find the most similar entity for each sentence.
        # The embeddings are normalized so the dot product is the cosine similarity
        similarity_matrix = util.dot_score(sentence_embeddings, entity_embeddings)
        most_similar_entity_scores, most_similar_entity_indices = torch.max(
            similarity_matrix, dim=-1
        )

        # Un-flatten the list of most similar entities to match the original texts
        entity_ids_per_text = []
        sentences = 0

        for text in texts:
            sentences_in_text = len(text)

            most_similar_entity_indices_text = most_similar_entity_indices[
                sentences : sentences + sentences_in_text
            ]
            most_similar_entity_scores_text = most_similar_entity_scores[
                sentences : sentences + sentences_in_text
            ]

            # Filter the entities based on the threshold
            most_similar_entity_indices_text = (
                most_similar_entity_indices_text[
                    torch.nonzero(most_similar_entity_scores_text > threshold)
                ]
                .squeeze(dim=-1)
                .unique()
                .tolist()
            )

            # Create a list of dictionaries containing the entities for the current text
            entity_ids_per_text.append(
                np.take(entity_ids, most_similar_entity_indices_text).tolist()
            )

            sentences += sentences_in_text

        return entity_ids_per_text

    @staticmethod
    def remove_embeddings(model_name: str = None):
        """
        This method removes the skill and occupation embeddings from the disk in case the model changed.
        This is useful to avoid loading the embeddings from the previous model.
        
        Args:
            model_name: If provided, only removes embeddings for this model. Otherwise removes all.
        """
        data_dir = f"{SkillExtractor._dir}/data/"
        
        if model_name:
            # Remove specific model embeddings
            model_hash = hashlib.md5(model_name.encode()).hexdigest()[:8]
            skill_file = f"{data_dir}skill_embeddings_{model_hash}.bin"
            occupation_file = f"{data_dir}occupation_embeddings_{model_hash}.bin"
            
            if os.path.exists(skill_file):
                os.remove(skill_file)
                print(f"Removed skill embeddings for {model_name}")
            if os.path.exists(occupation_file):
                os.remove(occupation_file)
                print(f"Removed occupation embeddings for {model_name}")
        else:
            # Remove all embedding files (both old and new format)
            for file in os.listdir(data_dir):
                if file.startswith(("skill_embeddings", "occupation_embeddings")) and file.endswith(".bin"):
                    os.remove(os.path.join(data_dir, file))
                    print(f"Removed {file}")

    def get_skills(self, texts: List[str], threshold: float = None) -> List[List[str]]:
        """
        This method extracts the ESCO skills from the texts.

        Args:
            texts (List[str]): The texts from which skills will be extracted.
            threshold (float, optional): Custom threshold for this request. If None, uses instance default.

        Returns:
            List[List[str]]: A list of lists containing the IDs of the skills for each text.
        """
        
        actual_threshold = threshold if threshold is not None else self.skills_threshold
        
        return self._get_entity(
            texts,
            self._skill_ids,
            self._skill_embeddings,
            actual_threshold,
        )

    def get_occupations(self, texts: List[str], threshold: float = None) -> List[List[str]]:
        """
        This method extracts the ESCO occupations from the texts.

        Args:
            texts (List[str]): The texts from which occupations will be extracted.
            threshold (float, optional): Custom threshold for this request. If None, uses instance default.

        Returns:
            List[List[str]]: A list of lists containing the IDs of the occupations for each text.
        """
        
        actual_threshold = threshold if threshold is not None else self.occupation_threshold
        
        return self._get_entity(
            texts,
            self._occupation_ids,
            self._occupation_embeddings,
            actual_threshold,
        )
