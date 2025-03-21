class TrieNode:
    """A node in the Trie data structure.
    
    Attributes:
        children (dict): Maps characters to child TrieNodes
        is_end (bool): True if this node represents the end of a word
    """
    def __init__(self):
        self.children: dict[str, 'TrieNode'] = {}
        self.is_end: bool = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for letter in word:
            if letter not in node.children:
                node.children[letter] = TrieNode()
            node = node.children[letter]
        node.is_end = True

    def search_with_constraints(self, required_letters: set[str], domains: list[set[str]]) -> list[str]:
        """Search for words matching given constraints.

        Args:
            required_letters: Letters that must appear in the word at least once
            domains: domains[i] contains allowed letters at position i

        Returns:
            List of valid words satisfying all constraints
        """
        results: list[str] = []
        self._dfs(
            node=self.root,
            prefix="",
            found_letters=set(),
            required_letters=required_letters,
            domains=domains,
            results=results
        )
        return results

    def _dfs(
        self,
        node: TrieNode,
        prefix: str,
        found_letters: set[str],
        required_letters: set[str],
        domains: list[set[str]],
        results: list[str]
    ) -> None:
        if node.is_end and required_letters.issubset(found_letters):
            results.append(prefix)
            
        index = len(prefix)
        if index >= len(domains):
            return
        
        for letter in domains[index]:
            if letter not in node.children:
                continue
                
            new_found = found_letters | {letter} if letter in required_letters else found_letters
            
            self._dfs(
                node=node.children[letter],
                prefix=prefix + letter,
                found_letters=new_found,
                required_letters=required_letters,
                domains=domains,
                results=results
            )