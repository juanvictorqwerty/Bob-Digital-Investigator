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
_trusted_suffixes: set[str] = set()
_cameroon_keywords: set[str] = set()
_government_tlds: set[str] = set()
_official_presidential_domains: set[str] = set()
_tier1_news_agencies: set[str] = set()
_tier1_african_news: set[str] = set()


def _load_config() -> dict:
    """
    Load the trusted domains JSON file.
    
    Returns:
        Dict with 'domains', 'certified_facebook_pages', and 'trusted_suffixes' keys.
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
    global _trusted_data, _trusted_domains, _certified_facebook_pages, _trusted_suffixes
    global _cameroon_keywords, _government_tlds, _official_presidential_domains
    global _tier1_news_agencies, _tier1_african_news
    
    _trusted_data = _load_config()
    _trusted_domains = set(_trusted_data.get('domains', []))
    _certified_facebook_pages = set(_trusted_data.get('certified_facebook_pages', []))
    _trusted_suffixes = set()
    for suffix in _trusted_data.get('trusted_suffixes', []):
        # Normalize: strip leading dot for consistency
        _trusted_suffixes.add(suffix.lower().lstrip('.'))
    
    _cameroon_keywords = set(_trusted_data.get('cameroon_keywords', []))
    _government_tlds = set(_trusted_data.get('government_tlds', []))
    _official_presidential_domains = set(_trusted_data.get('official_presidential_domains', []))
    _tier1_news_agencies = set(_trusted_data.get('tier1_news_agencies', []))
    _tier1_african_news = set(_trusted_data.get('tier1_african_news', []))
    
    logger.info(
        f"Loaded {len(_trusted_domains)} trusted domains, "
        f"{len(_certified_facebook_pages)} certified Facebook pages, "
        f"{len(_trusted_suffixes)} trusted suffixes, "
        f"{len(_cameroon_keywords)} Cameroon keywords, "
        f"{len(_government_tlds)} government TLDs, "
        f"{len(_official_presidential_domains)} official presidential domains, "
        f"{len(_tier1_news_agencies)} tier-1 news agencies, "
        f"{len(_tier1_african_news)} tier-1 African news outlets"
    )


# Load on import
reload_config()


def get_trusted_domains() -> set[str]:
    """Return the current set of trusted domains."""
    return _trusted_domains


def get_certified_facebook_pages() -> set[str]:
    """Return the current set of certified Facebook page usernames."""
    return _certified_facebook_pages


def get_trusted_suffixes() -> set[str]:
    """Return the current set of trusted suffixes (e.g., 'org', 'gov', 'edu')."""
    return _trusted_suffixes


def get_cameroon_keywords() -> set[str]:
    """Return the current set of Cameroon-related keywords."""
    return _cameroon_keywords


def get_government_tlds() -> set[str]:
    """Return the current set of government TLDs (e.g., '.gov', '.gov.cm')."""
    return _government_tlds


def get_official_presidential_domains() -> set[str]:
    """Return the current set of official presidential/government domains."""
    return _official_presidential_domains


def get_tier1_news_agencies() -> set[str]:
    """Return the current set of tier-1 international news agency domains."""
    return _tier1_news_agencies


def get_tier1_african_news() -> set[str]:
    """Return the current set of tier-1 African news outlet domains."""
    return _tier1_african_news


def has_trusted_suffix(domain: Optional[str]) -> bool:
    """
    Check if a domain contains a trusted suffix anywhere in its parts.
    
    A domain like 'example.org.cm' or 'university.edu.ru' will match if
    'org' or 'edu' is in the trusted_suffixes list.
    
    Args:
        domain: Domain string (e.g., 'bbc.org.cm', 'univ.edu.ru', 'reuters.com')
    
    Returns:
        True if any part of the domain matches a trusted suffix
    """
    if not domain:
        return False
    
    parts = domain.lower().split('.')
    for part in parts:
        if part in _trusted_suffixes:
            return True
    return False


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


def has_cameroon_keyword(text: Optional[str]) -> bool:
    """
    Check if text contains any Cameroon-related keyword.
    
    Args:
        text: Text to search (e.g., snippet, title)
    
    Returns:
        True if any Cameroon keyword is found in the text
    """
    if not text:
        return False
    
    text_lower = text.lower()
    for keyword in _cameroon_keywords:
        if keyword in text_lower:
            return True
    return False


def has_government_tld(domain: Optional[str]) -> bool:
    """
    Check if a domain ends with a government TLD.
    
    Args:
        domain: Domain string (e.g., 'example.gov', 'example.gov.cm')
    
    Returns:
        True if the domain ends with any government TLD
    """
    if not domain:
        return False
    
    domain_lower = domain.lower()
    for tld in _government_tlds:
        if domain_lower.endswith(tld):
            return True
    return False


def is_official_presidential_domain(domain: Optional[str]) -> bool:
    """
    Check if a domain is an official presidential or government domain.
    
    Args:
        domain: Domain string (e.g., 'prc.cm', 'whitehouse.gov')
    
    Returns:
        True if the domain is in the official presidential domains set
    """
    if not domain:
        return False
    
    return domain.lower() in _official_presidential_domains


def is_tier1_news_agency(domain: Optional[str]) -> bool:
    """
    Check if a domain is a tier-1 international news agency.
    
    Args:
        domain: Domain string (e.g., 'reuters.com', 'apnews.com')
    
    Returns:
        True if the domain is in the tier-1 news agencies set
    """
    if not domain:
        return False
    
    return domain.lower() in _tier1_news_agencies


def is_tier1_african_news(domain: Optional[str]) -> bool:
    """
    Check if a domain is a tier-1 African news outlet.
    
    Args:
        domain: Domain string (e.g., 'jeuneafrique.com', 'crtv.cm')
    
    Returns:
        True if the domain is in the tier-1 African news set
    """
    if not domain:
        return False
    
    return domain.lower() in _tier1_african_news


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