import json
import time
from pathlib import Path
from typing import Dict, List, TypedDict
import logging
from tqdm import tqdm

from wordle_agent import agent_play_Wordle

# Constants
OFFICIAL_WORDS_FILE = Path('wordle_words_official.txt')
VALIDATION_RESULTS_FILE = Path('wordle_validation_official.json')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class GameResult(TypedDict):
    win: bool
    attempts: int
    time: float
    answer: str | None

class WordleStats(TypedDict):
    avg_time: float
    avg_attempts: float
    lost_games: List[str]
    win_rate: float

def play_single_game(answer: str, word_length: int) -> GameResult:
    """Play a single Wordle game with the agent.
    
    Args:
        answer: The target word to guess
        word_length: Length of the word
        
    Returns:
        Dictionary containing game results including win status, attempts, time taken
    """
    try:
        start_time = time.time()
        win, attempts = agent_play_Wordle(word_length, answer, official_list=True)
        end_time = time.time()
        
        return {
            'win': win,
            'attempts': attempts,
            'time': end_time - start_time,
            'answer': answer if not win else None
        }
    except Exception as e:
        logging.error(f"Error playing game with answer '{answer}': {str(e)}")
        raise

def validate_wordle_agent() -> Dict[int, WordleStats]:
    """Validates the Wordle agent by playing games with all official words.
    
    Returns:
        Dictionary mapping word lengths to their statistics
    """
    stats: Dict[int, WordleStats] = {}
    
    try:
        # Read words from file
        if not OFFICIAL_WORDS_FILE.exists():
            raise FileNotFoundError(f"Words file not found: {OFFICIAL_WORDS_FILE}")
            
        with open(OFFICIAL_WORDS_FILE, 'r') as f:
            word_list = [word.strip() for word in f.readlines()]
        
        if not word_list:
            raise ValueError("Word list is empty")
            
        word_length = len(word_list[0])
        results: List[GameResult] = []

        # Process words with progress bar
        for answer in tqdm(word_list, desc="Playing games"):
            if len(answer) != word_length:
                logging.warning(f"Skipping word '{answer}' - incorrect length")
                continue
                
            result = play_single_game(answer, word_length)
            results.append(result)

        # Calculate statistics
        game_times = [r['time'] for r in results]
        lost_game_words = [r['answer'] for r in results if r['answer'] is not None]
        win_count = sum(1 for r in results if r['win'])
        total_attempts = sum(r['attempts'] for r in results)

        avg_time = sum(game_times) / len(game_times)
        avg_attempts = total_attempts / len(results)
        
        logging.info(f"Average time per game: {avg_time:.2f} seconds")
        logging.info(f"Average attempts per game: {avg_attempts:.2f}")
        logging.info(f"Lost {len(lost_game_words)} of {len(results)} games")
        
        stats[word_length] = {
            'avg_time': avg_time,
            'avg_attempts': avg_attempts,
            'lost_games': lost_game_words,
            'win_rate': win_count / len(results)
        }
        
        # Save results
        with open(VALIDATION_RESULTS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logging.info(f"Results saved to {VALIDATION_RESULTS_FILE}")
            
    except Exception as e:
        logging.error(f"Validation failed: {str(e)}")
        raise
        
    return stats

def print_validation_summary(validation_stats: Dict[int, WordleStats]) -> None:
    """Print a summary of the validation results.
    
    Args:
        validation_stats: Dictionary of validation statistics by word length
    """
    logging.info("\nValidation Summary:")
    for word_length, stats in validation_stats.items():
        logging.info(f"\n{word_length}-letter words:")
        logging.info(f"Win rate: {stats['win_rate']*100:.1f}%")
        logging.info(f"Average attempts: {stats['avg_attempts']:.2f}")
        logging.info(f"Average time: {stats['avg_time']:.2f} seconds")
        if stats['lost_games']:
            logging.info(f"Lost games ({len(stats['lost_games'])}): {', '.join(stats['lost_games'])}")

if __name__ == '__main__':
    try:
        validation_stats = validate_wordle_agent()
        print_validation_summary(validation_stats)
    except Exception as e:
        logging.error(f"Program failed: {str(e)}")
        exit(1)