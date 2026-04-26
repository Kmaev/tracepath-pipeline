class TrieNode:
    def __init__(self):
        self.children = {}
        self.end_of_word = False


class Trie:
    """Store a single trie node."""

    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        """
        Insert a word into the trie.

        Args:
            word: Word to insert.
        """
        cur = self.root
        """
         We check each character in the word to see if it is already among the 
        previously inserted characters (nodes) in the tree.
        """
        for char in word:
            if char not in cur.children:
                # If the character is not among the existing children/nodes, we insert it as a new Trie node.
                cur.children[char] = TrieNode()
            cur = cur.children[char]  # If the character already exists, set it as the current node.

        cur.end_of_word = True

    def starts_with_prefix(self, prefix: str) -> TrieNode | None:
        """
        Return the node matching the given prefix.

        Args:
            prefix: Prefix to search.
        """
        node = self.root
        for char in prefix:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def collect_words(self, node: TrieNode, prefix: str, results: list[str]) -> None:
        """
        Collect words from the given node.

        Args:
            node: Starting node.
            prefix: Current prefix.
            results: Output list of words.
        """
        if node.end_of_word:
            results.append(prefix)  # if all word found it is added to the result

        for char, next_node in node.children.items():
            self.collect_words(next_node, prefix + char, results)

    def autocomplete(self, prefix: str) -> list[str]:
        """
        Return words starting with the given prefix.

        Args:
            prefix: Prefix to search.
        """
        node = self.starts_with_prefix(prefix)
        results = []
        if node:
            self.collect_words(node, prefix, results)
        return results
