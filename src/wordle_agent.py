from playwright.sync_api import sync_playwright
from word_cache_creation import get_words
from trie_search import Trie
import math

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = {var: set(domains) for var in variables}
        self.constraints = constraints

def get_word_list(word_length, wordle_official=False):
    """
    Get a list of valid words of the specified length.
    
    Args:
        word_length (int): The desired length of words to return
        wordle_official (bool): If True, use official list of valid Wordle guesses,
                               if False, use expanded dictionary
    
    Returns:
        list: A list of lowercase strings of length word_length
    """
    # Use official Wordle word list if specified
    if wordle_official:
        with open('wordle_words_official.txt', 'r') as f:
            # Read file, strip whitespace, convert to lowercase
            return [word.strip().lower() for word in f.readlines()]
    
    # Otherwise use expanded dictionary filtered by word length
    return get_words(word_length)

def build_conflict_tuples(guesses, domains_list):
    """
    Identify multi-letter positions in domains_list, then
    for each guess word, build tuples containing letters at those positions.
    The length of each tuple equals the number of multi-letter domains.
    """
    # Which positions in the domain have length>1?
    multi_positions = [i for i, dom in enumerate(domains_list) if len(dom) > 1]

    conflict_tuples = set()
    for w in guesses:
        # For this word, take letters at all multi-letter positions
        conflict_tuple = tuple(w[i] for i in multi_positions)
        conflict_tuples.add(conflict_tuple)

    return conflict_tuples

def get_feedback(guess, answer):
    feedback = [0] * len(guess)
    answer_chars = list(answer)

    # First pass: Check for correct letters in the correct position.
    for i in range(len(guess)):
        if guess[i] == answer[i]:
            feedback[i] = 2
            answer_chars[i] = None  # Remove matched letter.

    # Second pass: Check for correct letters in the wrong position.
    for i in range(len(guess)):
        if feedback[i] == 0 and guess[i] in answer_chars:
            feedback[i] = 1
            answer_chars[answer_chars.index(guess[i])] = None

    return tuple(feedback)

def get_all_feedback_patterns(word_length=5):
    # Generate all possible feedback patterns (3^n combinations of 0,1,2)
    def generate_patterns_recursive(length, current=[]):
        if length == 0:
            patterns.append(tuple(current))
            return
        for i in range(3):
            generate_patterns_recursive(length - 1, current + [i])
    
    patterns = []
    generate_patterns_recursive(word_length)
    return patterns

def compute_new_entropy(solution, candidates):
    """
    Compute entropy for a potential answer given the candidate list.
    
    Args:
        solution (str): The potential guess to evaluate
        candidates (list[str]): List of possible answers
    
    Returns:
        float: Entropy for this guess
    """
    n = len(candidates)
    word_length = len(candidates[0])
    if n == 0:
        return 0
        
    feedback_patterns = {pattern: 0 for pattern in get_all_feedback_patterns(word_length)}
    for s in candidates:
        pattern = get_feedback(s, solution)
        feedback_patterns[pattern] += 1
    feedback_distribution = {k: v/n for k, v in feedback_patterns.items()}
    return -sum(prob * math.log2(prob) 
               for prob in feedback_distribution.values() 
               if prob > 0)

def get_max_entropy_guess(guesses):
    """
    Find the guess that provides maximum information gain by maximizing entropy.
    
    Args:
        guesses (list[str]): List of possible guesses
    
    Returns:
        str: The most informative guess
    """
    guess_entropies = [compute_new_entropy(guess, guesses) 
                      for guess in guesses]
    selected_guess_idx = guess_entropies.index(max(guess_entropies))
    return guesses[selected_guess_idx]

def _process_green_letters(previous_word, feedback, yellow_letters, csp):
    """Process green (correct position) letters from feedback."""
    for i, (letter, result) in enumerate(zip(previous_word, feedback)):
        if result == 2:
            if letter in yellow_letters:
                yellow_letters.discard(letter)
            csp.domains[i] = {letter}

def _process_yellow_grey_letters(previous_word, feedback, yellow_letters, csp):
    """Process yellow and grey letters from feedback."""
    grey_letters = set()
    for i, (letter, result) in enumerate(zip(previous_word, feedback)):
        if result == 0:
            grey_letters.add(letter)
        elif result == 1:
            csp.domains[i].discard(letter)
            yellow_letters.add(letter)
    return grey_letters

def _calculate_word_score(word, unsolved_letters_list, domains_list, conflict_tuples, unsolved_letters_priority):
    """Calculate score for a candidate word."""
    remaining_letters = unsolved_letters_list.copy()
    for letter in set(word):
        if letter in remaining_letters:
            remaining_letters.remove(letter)
    
    score = len(unsolved_letters_list) - len(remaining_letters)
    
    # Check conflict tuples
    multi_positions = [i for i, dom in enumerate(domains_list) if len(dom) > 1]
    word_tuple = tuple(word[i] for i in multi_positions)
    if any(len(set(word_tuple) & set(ct)) > 1 for ct in conflict_tuples):
        score = 0
    
    starts_with_priority = bool(word and word[0] in unsolved_letters_priority)
    return score, starts_with_priority

def guess(guessed_words, yellow_letters, feedback, csp, trie):
    """
    Generate the next optimal guess for Wordle based on previous guesses and feedback.
    
    This function implements a hybrid strategy that combines constraint satisfaction
    with information gain optimization. It processes feedback from previous guesses
    to maintain letter constraints and domains, then selects the next guess using
    either a letter-frequency based scoring system (when more than half the letters
    are known) or maximum information gain (in early game stages).
    
    Args:
        guessed_words (List[str]): List of previously attempted words
        yellow_letters (Set[str]): Set of letters known to be in the word but in wrong positions
        feedback (List[int]): Feedback from previous guess where:
            - 2 = correct letter in correct position (green)
            - 1 = correct letter in wrong position (yellow)
            - 0 = letter not in word (grey)
        csp (CSP): Constraint satisfaction problem instance containing:
            - variables: positions in the word (0 to word_length-1)
            - domains: possible letters for each position
        trie (Trie): Trie data structure containing valid word list for efficient search
        
    Returns:
        str: The next word to guess
        
    Raises:
        ValueError: If there's a length mismatch between previous word, feedback,
                  and CSP variables
    
    Strategy:
    1. Updates CSP domains based on feedback from previous guess
    2. If remaining valid words <= remaining attempts, returns first valid word
    3. For late game (>50% letters known):
       - Scores candidate words based on unsolved letter coverage
       - Penalizes words with letter patterns matching previous incorrect guesses
       - Prioritizes words starting with letters from unsolved positions
    4. For early game:
       - Uses information gain optimization to maximize letter information
    """
    # Input validation
    previous_word = list(guessed_words[-1])
    word_length = len(guessed_words[0])
    if len(previous_word) != len(feedback) or len(previous_word) != len(csp.variables):
        raise ValueError("Length mismatch between previous word, feedback and variables")

    # Process feedback
    _process_green_letters(previous_word, feedback, yellow_letters, csp)
    grey_letters = _process_yellow_grey_letters(previous_word, feedback, yellow_letters, csp)
    
    # Apply constraints and get valid guesses
    for i in csp.variables:
        if len(csp.domains[i]) > 1:
            csp.domains[i] -= (grey_letters - yellow_letters)
    
    guesses = [word for word in trie.search_with_constraints(yellow_letters, list(csp.domains.values()))
               if word not in guessed_words]
    
    # Update domains based on valid guesses
    for i in csp.variables:
        if len(csp.domains[i]) > 1:
            csp.domains[i] = {word[i] for word in guesses}

    # Early return if few possibilities remain
    attempt_num = len(guessed_words) + 1
    remaining_attempts = 6 - attempt_num + 1
    if len(guesses) <= remaining_attempts:
        return guesses[0]

    # Analyze current state
    domains_list = list(csp.domains.values())
    correctly_guessed = sum(1 for domain in domains_list if len(domain) == 1)
    
    # Build letter lists
    unsolved_letters = []
    solved_letters = []
    for domain in domains_list:
        if len(domain) == 1:
            solved_letters.extend(list(domain))
        else:
            unsolved_letters.extend(list(domain))
    
    for letter in solved_letters:
        if letter in unsolved_letters:
            unsolved_letters.remove(letter)
    
    unsolved_letters_priority = next((domain for domain in domains_list if len(domain) > 1), set())

    # Choose strategy based on game state
    if correctly_guessed > (word_length-1)/2 and len(guesses) > 1 and attempt_num < 6:
        # Late game strategy
        loosest_domain = [set('abcdefghijklmnopqrstuvwxyz') for _ in range(word_length)]
        candidate_words = trie.search_with_constraints(set(), loosest_domain)
        conflict_tuples = build_conflict_tuples(guesses, domains_list)
        
        # Score all possible words
        word_scores = [
            (*_calculate_word_score(word, unsolved_letters, domains_list, 
                                  conflict_tuples, unsolved_letters_priority), word)
            for word in guesses + candidate_words
        ]
        
        if word_scores:
            word_scores.sort(key=lambda x: (x[0], x[1]), reverse=True)
            return word_scores[0][2]
    
    # Early game strategy
    return get_max_entropy_guess(guesses)
    


def agent_play_Wordle(word_length: int, answer: str, official_list: bool = False) -> tuple[int, int]:
    """
    Play a game of Wordle using the agent strategy.
    
    Args:
        word_length (int): Length of the target word
        answer (str): The word to be guessed
        official_list (bool): If True, use official Wordle word list, otherwise use expanded dictionary
    
    Returns:
        tuple[int, int]: A tuple containing:
            - Success flag (1 for win, 0 for loss)
            - Number of attempts used
            
    Raises:
        ValueError: If word_length doesn't match answer length or is invalid
    """
    # Input validation
    if not isinstance(word_length, int) or word_length < 1:
        raise ValueError("word_length must be a positive integer")
    if len(answer) != word_length:
        raise ValueError(f"Answer length ({len(answer)}) doesn't match word_length ({word_length})")
    
    # Initialize game state
    domain = set("abcdefghijklmnopqrstuvwxyz")
    variables = list(range(word_length))
    word_list = get_word_list(word_length, official_list)
    
    # Set up trie for efficient word lookup
    trie = Trie()
    for word in word_list:
        trie.insert(word)

    # Initialize CSP solver
    csp = CSP(variables, domain, None)
    
    # Game state variables
    max_attempts = 6
    guessed_words = []
    yellow_letters = set()
    feedback = [0] * word_length
    
    # Main game loop
    for attempt_num in range(1, max_attempts + 1):
        # Select guess based on game state
        current_guess = word_list[0] if attempt_num == 1 else \
                       guess(guessed_words, yellow_letters, feedback, csp, trie)
        
        guessed_words.append(current_guess)
        feedback = get_feedback(current_guess, answer)
        
        # Early return on correct guess
        if current_guess == answer:
            return 1, attempt_num
    
    return 0, max_attempts


    
def agent_play_Wordle_official():
    """
    Simplified version of the user_play_Wordle() function suitable for the agent.
    Interacts dynamically with today's NY Times Wordle puzzle via Playwright's browser automation
    """
    domain = set("abcdefghijklmnopqrstuvwxyz")  # 26-letter alphabet domain
    variables = [i for i in range(5)]
    word_list = get_word_list(5,True)
    trie = Trie()
    for word in word_list:
        trie.insert(word)


    # Create CSP
    csp = CSP(variables, domain, None)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to False to observe actions
        page = browser.new_page()
        page.goto("https://www.nytimes.com/games/wordle/index.html", wait_until="domcontentloaded")  # Ensures full page load
        # Add a 5 second pause
        page.wait_for_timeout(5000)

        page.click("button.purr-blocker-card__button")

        page.click("button[data-testid='Play']")

        page.click("path[d='M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z']")

        page.click("button[data-key='q']")
        page.keyboard.press('Backspace')
        feedback = []
        guessed_words = []
        yellow_letters = set()
        attempt = 1
        while feedback != [2,2,2,2,2]:  # Continue until word is correctly guessed
            
            if attempt == 1:
                # word_list has been sorted by decreasing information gain
                # the intial guess yielding the most information could have been computed here
                # but it was pre-computed to reduce latency
                current_guess = word_list[0]
            else:
                current_guess = guess(guessed_words,yellow_letters,feedback,csp,trie)
            # Type the provided guess
            guessed_words.append(current_guess)
            page.keyboard.type(current_guess)
            page.keyboard.press('Enter')
            # Add a 5 second pause after entering the guess
            page.wait_for_timeout(5000)
            # Wait for tiles to update their state
            page.wait_for_selector("div.Tile-module_tile__UWEHN[data-state]", timeout=10000)

            # Get tiles from the current row only
            current_row = page.query_selector(f'div[aria-label="Row {attempt}"]')
            tiles = current_row.query_selector_all("div.Tile-module_tile__UWEHN")
            
            feedback = []
            
            # Map tile states to feedback values
            state_to_feedback = {
                "present": 1,  # Letter exists but wrong position
                "correct": 2,  # Letter in correct position
                "absent": 0    # Letter not in word
            }
            
            for tile in tiles:
                state = tile.get_attribute("data-state")
                feedback.append(state_to_feedback.get(state, 0))
            attempt += 1
        page.wait_for_timeout(15000)
        browser.close()
