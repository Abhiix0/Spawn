import re

_USERINFO_RE = re.compile(r"((?>[a-zA-Z][a-zA-Z0-9+.-]{0,63}://))[^/@\s]+@")


def redact_url(text: str) -> str:
    """Strip ``user:token@`` userinfo from any ``scheme://user:token@host`` in text."""
    if "://" not in text or "@" not in text:
        return text
    return _USERINFO_RE.sub(r"\1", text)
