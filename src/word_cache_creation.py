import json
import logging
from pathlib import Path
import re
from typing import Dict, List, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Use Path objects for file handling
DICT_FILE = Path("expanded_word_list.txt")
CACHE_FILE = Path("word_cache.json")

def is_valid_word(word: str) -> bool:
    """
    Check if a word contains only lowercase letters a-z.
    
    Args:
        word: The word to validate
        
    Returns:
        bool: True if the word is valid, False otherwise
    """
    return re.fullmatch(r"[a-z]+", word) is not None

def build_word_cache() -> None:
    """
    Build a cache of words grouped by length from the dictionary file.
    Saves the cache to a JSON file.
    """
    word_cache: Dict[int, Set[str]] = {}
    
    try:
        logging.info(f"Building word cache from {DICT_FILE}")
        with DICT_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if is_valid_word(word):
                    length = len(word)
                    if length not in word_cache:
                        word_cache[length] = set()
                    word_cache[length].add(word)

        # Convert sets to lists before saving
        serializable_cache = {str(k): sorted(list(v)) for k, v in word_cache.items()}
        
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(serializable_cache, f, indent=2)
        logging.info(f"Word cache saved to {CACHE_FILE}")
        
    except IOError as e:
        logging.error(f"Error accessing files: {e}")
        raise

def get_words(n: int) -> List[str]:
    """
    Retrieve words of specified length from the cache.
    
    Args:
        n: The length of words to retrieve
        
    Returns:
        List[str]: List of words with the specified length
    """
    try:
        # Rebuild cache if it doesn't exist or is older than the dictionary
        if not CACHE_FILE.exists() or CACHE_FILE.stat().st_mtime < DICT_FILE.stat().st_mtime:
            build_word_cache()
        
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            word_cache = json.load(f)
        
        return word_cache.get(str(n), [])
    
    except IOError as e:
        logging.error(f"Error accessing cache file: {e}")
        return []

if __name__ == "__main__":
    build_word_cache()

