"""
API Key Manager with rotation support for handling rate limits.
Supports both single key and multiple keys (round-robin rotation).
"""

from typing import List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Manage multiple API keys with automatic rotation on failure.
    
    Example:
        manager = APIKeyManager(["key1", "key2", "key3"])
        key = manager.get_current_key()
        # if error due to rate limit, call manager.report_error(key)
        # next call will use next key
    """
    
    def __init__(self, keys: Union[str, List[str]], service_name: str = "unknown"):
        """
        Initialize key manager.
        
        Args:
            keys: Single key string or list of keys.
            service_name: Name of the API service (for logging).
        """
        if isinstance(keys, str):
            self.keys = [keys]
        else:
            self.keys = keys[:]  # copy
        
        self.service_name = service_name
        self.current_idx = 0
        self.key_attempts = {key: 0 for key in self.keys}
        self.max_attempts_per_key = 3  # can be adjusted
        
    def get_current_key(self) -> Optional[str]:
        """Return current active API key, or None if no keys available."""
        if not self.keys:
            logger.error(f"No API keys available for {self.service_name}")
            return None
        key = self.keys[self.current_idx]
        self.key_attempts[key] += 1
        return key
    
    def report_error(self, key: str, error_msg: str = ""):
        """
        Report an error (e.g., rate limit) for a key.
        If key exceeded max attempts, rotate to next key.
        """
        if key not in self.key_attempts:
            return
        
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            logger.warning(f"Rate limit hit for key {key[:8]}... on {self.service_name}")
            self._rotate()
        elif self.key_attempts[key] >= self.max_attempts_per_key:
            logger.warning(f"Key {key[:8]}... reached max attempts, rotating")
            self._rotate()
    
    def _rotate(self):
        """Rotate to the next available key."""
        if len(self.keys) <= 1:
            return
        self.current_idx = (self.current_idx + 1) % len(self.keys)
        logger.info(f"Rotated API key for {self.service_name}, now using index {self.current_idx}")
    
    def add_key(self, key: str):
        """Dynamically add a new key."""
        if key not in self.keys:
            self.keys.append(key)
            self.key_attempts[key] = 0
    
    def remove_key(self, key: str):
        """Remove a key (e.g., if revoked)."""
        if key in self.keys:
            idx = self.keys.index(key)
            self.keys.pop(idx)
            del self.key_attempts[key]
            if self.current_idx >= len(self.keys):
                self.current_idx = 0


# Convenience function for usage with config settings
def create_gemini_key_manager() -> "APIKeyManager":
    """Factory to create key manager for Gemini using config settings."""
    from config.settings import GEMINI_API_KEY
    return APIKeyManager(GEMINI_API_KEY, service_name="Gemini")


def create_jina_key_manager() -> "APIKeyManager":
    """Factory for Jina API (single key for now)."""
    from config.settings import JINA_API_KEY
    if JINA_API_KEY is None:
        raise ValueError("JINA_API_KEY not set in .env")
    return APIKeyManager(JINA_API_KEY, service_name="Jina")