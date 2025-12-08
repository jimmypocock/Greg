"""
Search module exceptions.

Domain-specific exceptions for web search operations.
"""


class SearchError(Exception):
    """Base exception for search errors."""

    def __init__(self, message: str = "Search error"):
        self.message = message
        super().__init__(self.message)


class EmptyQueryError(SearchError):
    """Raised when search query is empty."""

    def __init__(self):
        super().__init__("Search query cannot be empty")


class InvalidModelError(SearchError):
    """Raised when model name is invalid."""

    def __init__(self, model_name: str):
        super().__init__(f"Invalid model name: {model_name}")


class WebSearchError(SearchError):
    """Raised when web search fails."""

    def __init__(self, message: str = "Web search failed"):
        super().__init__(message)
