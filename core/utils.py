import re
from urllib.parse import urlparse
from typing import Optional, Union

# Import your services config
from core.service_config import services

def pattern_to_regex(pattern: str) -> str:
    """Convert pattern to regex — allows trailing query params"""
    regex = ""
    in_query = False  # Track if we've passed the ? separator
    i = 0
    
    while i < len(pattern):
        char = pattern[i]
        
        # ─────────────────────────────────────
        # Detect start of query string (only once per pattern)
        # ─────────────────────────────────────
        if char == '?' and not in_query:
            regex += r'\?'  # Escape the literal ? separator
            in_query = True
            i += 1
            continue
        
        # ─────────────────────────────────────
        # Handle :paramName (e.g., :id, :userId, :postId)
        # ─────────────────────────────────────
        if char == ':':
            # Extract the full parameter name
            param_name = ""
            j = i + 1
            while j < len(pattern) and pattern[j] not in '/?&#':
                param_name += pattern[j]
                j += 1
            
            if not param_name:
                # Edge case: lone : with no name → treat as literal
                regex += re.escape(char)
                i += 1
                continue
            
            # Choose what the param matches based on context
            if in_query:
                # Query param: match until & or end of string
                # Example: &t=:time → (?P<time>[^&]+)
                regex += f"(?P<{param_name}>[^&]+)"
            else:
                # Path param: match until / or end of string
                # Example: /video/:id → /video/(?P<id>[^/]+)
                regex += f"(?P<{param_name}>[^/]+)"
            
            # Skip ahead to end of parameter name
            i = j
            continue
        
        # ─────────────────────────────────────
        # Escape regex special characters (except / and - and _ which are safe)
        # ─────────────────────────────────────
        if char in '.^$*+{}[]\\|()':
            regex += '\\' + char
        else:
            regex += char
        
        i += 1
    
    # ─────────────────────────────────────
    # Anchor to START only (not end)
    # This allows trailing query params like &t=123&feature=share
    # ─────────────────────────────────────
    return f"^{regex}"


def get_service_from_url(url: str) -> Optional[str]:
    """
    Extract the service name (e.g., "youtube") from a URL.
    
    Uses tldextract to correctly handle domains like:
    - youtube.com → "youtube"
    - m.youtube.com → "youtube" 
    - bilibili.tv → "bilibili"
    - fb.watch → "fb" (then we check altDomains)
    
    Returns:
        Service name string if found in config, None otherwise
    """
    import tldextract
    
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    if not hostname:
        return None
    
    # Extract domain parts using public suffix list
    extracted = tldextract.extract(hostname)
    domain = extracted.domain  # e.g., "youtube" from "youtube.com"
    
    # Direct match: domain is the service name
    if domain and domain in services:
        return domain
    
    # Check altDomains for services like twitter.com / x.com
    for service_name, config in services.items():
        if hostname in config.get("altDomains", []):
            return service_name
    
    return None

