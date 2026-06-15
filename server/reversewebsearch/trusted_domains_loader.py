"""
Loader for trusted domains and certified Facebook pages from JSON configuration.

Reads trusted_domains.json and provides helper functions to check
whether a domain or Facebook page is trusted/certified.
"""

import json
import logging
import os
from urllib.parse import urlparse
from typing import Optional

logger = logging.getLogger(__name__)

# Path to the JSON config file (relative to this module)
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'trusted_domains.json')

# Cached data loaded once on import
_trusted_data: dict = {}
_trusted_domains: set[str] = set()
_certified_facebook_pages: set[str] = set()


def _load_config() -> dict:
    """
    Load the trusted domains JSON file.
    
    Returns:
        Dict with 'domains' and 'certified_facebook_pages' keys.
        Returns empty dict on failure.
    """
    try:
        with open(_CONFIG_PATH, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        logger.warning(f"Trusted domains config not found at {_CONFIG_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in trusted domains config: {e}")
        return {}


def reload_config() -> None:
    """
    Reload the configuration from disk.
    
    Call this if the JSON file is updated at runtime.
    """
    global _trusted_data, _trusted_domains, _certified_facebook_pages
    
    _trusted_data = _load_config()
    _trusted_domains = set(_trusted_data.get('domains', []))
    _certified_facebook_pages = set(_trusted_data.get('certified_facebook_pages', []))
    
    logger.info(
        f"Loaded {len(_trusted_domains)} trusted domains "
        f"and {len(_certified_facebook_pages)} certified Facebook pages"
    )


# Load on import
reload_config()


def get_trusted_domains() -> set[str]:
    """Return the current set of trusted domains."""
    return _trusted_domains


def get_certified_facebook_pages() -> set[str]:
    """Return the current set of certified Facebook page usernames."""
    return _certified_facebook_pages


def is_trusted_domain(domain: Optional[str]) -> bool:
    """
    Check if a domain is in the trusted list.
    
    Supports direct match and subdomain match (e.g., sub.bbc.com → bbc.com).
    
    Args:
        domain: Domain string (e.g., 'bbc.com', 'www.facebook.com')
    
    Returns:
        True if the domain or its parent domain is trusted
    """
    if not domain:
        return False
    
    domain = domain.lower()
    
    # Direct match
    if domain in _trusted_domains:
        return True
    
    # Subdomain match (e.g., sub.bbc.com → bbc.com)
    parts = domain.split('.')
    for i in range(1, len(parts) - 1):
        parent = '.'.join(parts[i:])
        if parent in _trusted_domains:
            return True
    
    return False


def extract_facebook_page_username(url: Optional[str]) -> Optional[str]:
    """
    Extract the Facebook page username from a Facebook URL.
    
    Examples:
        https://www.facebook.com/bbcnews        → 'bbcnews'
        https://facebook.com/Reuters            → 'Reuters'
        https://www.facebook.com/pages/...      → None (not a simple page URL)
        https://www.facebook.com/photo.php      → None
    
    Args:
        url: A Facebook page URL
    
    Returns:
        The page username if extractable, None otherwise
    """
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Must be facebook.com or fb.com
        if not (domain.endswith('facebook.com') or domain.endswith('fb.com')):
            return None
        
        path = parsed.path.strip('/')
        
        # Simple page URL: facebook.com/Username
        # Path should be a single segment, not starting with known prefixes
        if not path or '/' in path:
            return None
        
        # Exclude known non-page paths
        excluded_prefixes = {
            'photo.php', 'video.php', 'story.php', 'watch', 'login',
            'signup', 'settings', 'pages', 'groups', 'events', 'messages',
            'notifications', 'friends', 'marketplace', 'gaming', 'live',
            'reel', 'reels', 'shorts'
        }
        
        username = path.split('/')[0].split('?')[0]
        
        if username.lower() in excluded_prefixes:
            return None
        
        return username if username else None
        
    except Exception:
        return None


def is_certified_facebook_page(url: Optional[str]) -> bool:
    """
    Check if a URL points to a certified Facebook page.
    
    Args:
        url: A Facebook page URL
    
    Returns:
        True if the URL is a Facebook page whose username is in the certified list
    """
    if not url:
        return False
    
    username = extract_facebook_page_username(url)
    if not username:
        return False
    
    return username.lower() in {u.lower() for u in _certified_facebook_pages}