import re


_GITHUB_PATTERNS = (
    r"^https://github\.com/[a-zA-Z0-9][a-zA-Z0-9_-]*/[a-zA-Z0-9][a-zA-Z0-9_.-]*/?$",
    r"^https://github\.com/[a-zA-Z0-9][a-zA-Z0-9_-]*/[a-zA-Z0-9][a-zA-Z0-9_.-]*\.git$",
    r"^git@github\.com:[a-zA-Z0-9][a-zA-Z0-9_-]*/[a-zA-Z0-9][a-zA-Z0-9_.-]*\.git$",
)


def is_valid_github_url(url: str) -> bool:
    """
    Validate supported GitHub repository URLs.
    """
    url = url.strip()

    if not url:
        return False

    return any(re.match(pattern, url) for pattern in _GITHUB_PATTERNS)
