import json
import time
import random
import logging
from typing import Dict, List, Optional
from pathlib import Path
from wordle_agent import agent_play_Wordle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
MAX_WORD_LENGTH = 9
OUTPUT_FILE = 'wordle_validation.json'

def play_single_game(
    answer: str,
    word_length: int,
) -> Dict:
    """
    Play a single Wordle game.
    
    Args:
        answer: The target word to guess
        word_length: Length of the word
    
    Returns:
        Dict containing game results (win status, attempts, time, answer if lost)
    """
    start_time = time.time()
    win, attempts = agent_play_Wordle(word_length, answer)
    end_time = time.time()
    
    return {
        'win': win,
        'attempts': attempts,
        'time': end_time - start_time,
        'answer': answer if not win else None
    }

def process_game_results(results: List[Dict]) -> Dict:
    """
    Process a batch of game results and compute statistics.
    
    Args:
        results: List of game result dictionaries
    
    Returns:
        Dict containing computed statistics
    """
    game_times = [r['time'] for r in results]
    lost_games = [r['answer'] for r in results if r['answer'] is not None]
    win_count = sum(1 for r in results if r['win'])
    total_attempts = sum(r['attempts'] for r in results)

    return {
        'avg_time': sum(game_times) / len(game_times),
        'avg_attempts': total_attempts / len(results),
        'lost_games': lost_games,
        'win_rate': win_count / len(results)
    }

def validate_wordle_agent(word_cache: Dict[str, List[str]]) -> Dict:
    """
    Validates the Wordle agent by playing games with words from the cache.
    
    Args:
        word_cache: Dictionary mapping word lengths to lists of words
    
    Returns:
        Dict containing validation statistics for each word length
    """
    stats = {}
    
    for key in word_cache:
        word_length = int(key)
        if word_length > MAX_WORD_LENGTH:
            continue
            
        stats[word_length] = {}
        logging.info(f"Testing word_length={word_length}")
        
        # Sample words for testing
        word_list = random.sample(
            word_cache[str(word_length)],
            min(1000, len(word_cache[str(word_length)]))
        )
        results = []

        # Process words sequentially
        for i, answer in enumerate(word_list, 1):
            logging.debug(f"Playing game {i}/{len(word_list)}. Answer = {answer}")
            try:
                result = play_single_game(answer, word_length)
                results.append(result)
            except Exception as e:
                logging.error(f"Error playing game with word '{answer}': {str(e)}")
                continue

        # Process and store results
        stats[word_length] = process_game_results(results)
        
        # Save intermediate results
        try:
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(stats, f, indent=2)
            logging.info(f"Results saved for word_length={word_length}")
        except Exception as e:
            logging.error(f"Error saving results: {str(e)}")
    
    return stats

def print_validation_summary(validation_stats: Dict) -> None:
    """
    Print a summary of the validation results.
    
    Args:
        validation_stats: Dictionary containing validation statistics
    """
    logging.info("\nValidation Summary:")
    for word_length, stats in validation_stats.items():
        logging.info(f"\n{word_length}-letter words:")
        logging.info(f"Win rate: {stats['win_rate']*100:.1f}%")
        logging.info(f"Average attempts: {stats['avg_attempts']:.2f}")
        logging.info(f"Average time: {stats['avg_time']:.2f} seconds")
        if stats['lost_games']:
            logging.info(f"Lost games ({len(stats['lost_games'])}): {', '.join(stats['lost_games'])}")

def main():
    """Main entry point for the Wordle agent validation script."""
    try:
        # Load word cache
        with open('word_cache.json', 'r') as f:
            word_cache = json.load(f)
    except FileNotFoundError:
        logging.error("word_cache.json not found")
        return
    except json.JSONDecodeError:
        logging.error("Invalid JSON in word_cache.json")
        return

    # Run validation
    validation_stats = validate_wordle_agent(word_cache)
    
    # Print summary
    print_validation_summary(validation_stats)

if __name__ == '__main__':
    main()


        