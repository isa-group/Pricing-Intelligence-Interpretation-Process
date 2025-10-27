"""
API Key Manager for A-MINT.
Handles rotation of API keys when quota limits are reached.
"""
import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class APIKeyStatus:
    """Status information for an API key."""
    key: str
    is_active: bool = True
    last_quota_error: Optional[datetime] = None
    error_count: int = 0
    cooldown_until: Optional[datetime] = None
    
    def is_in_cooldown(self) -> bool:
        """Check if the API key is currently in cooldown."""
        if self.cooldown_until is None:
            return False
        return datetime.now() < self.cooldown_until
    
    def mark_quota_error(self, cooldown_minutes: int = 60):
        """Mark this key as having hit a quota error."""
        self.last_quota_error = datetime.now()
        self.error_count += 1
        self.is_active = False
        self.cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        logger.warning(f"API key {self.key[:8]}... marked as inactive due to quota error. "
                      f"Cooldown until: {self.cooldown_until}")
    
    def reset_errors(self):
        """Reset error status for this key."""
        self.is_active = True
        self.error_count = 0
        self.last_quota_error = None
        self.cooldown_until = None

class APIKeyManager:
    """Manages rotation and status of API keys."""
    
    def __init__(self, api_keys: List[str], cooldown_minutes: int = 2):
        """
        Initialize the API Key Manager.
        
        Args:
            api_keys: List of API keys to manage
            cooldown_minutes: Minutes to wait before retrying a failed key
        """
        if not api_keys:
            raise ValueError("At least one API key must be provided")
        
        self.cooldown_minutes = cooldown_minutes
        self.key_statuses = [APIKeyStatus(key) for key in api_keys]
        self.current_index = 0
        logger.info(f"Initialized API Key Manager with {len(api_keys)} keys")
    
    def get_current_key(self) -> str:
        """Get the current active API key."""
        return self.key_statuses[self.current_index].key
    
    def get_available_key(self) -> Optional[str]:
        """
        Get an available API key, rotating if necessary.
        
        Returns:
            Available API key or None if all keys are in cooldown
        """
        # First, check if current key is still available
        current_status = self.key_statuses[self.current_index]
        if current_status.is_active and not current_status.is_in_cooldown():
            return current_status.key
        
        # Try to find another available key
        for i, status in enumerate(self.key_statuses):
            if status.is_active and not status.is_in_cooldown():
                self.current_index = i
                logger.info(f"Switched to API key {status.key[:8]}... (index {i})")
                return status.key
        
        # Check if any keys have completed their cooldown
        self._check_cooldown_recovery()
        
        # Try again after cooldown check
        for i, status in enumerate(self.key_statuses):
            if status.is_active and not status.is_in_cooldown():
                self.current_index = i
                logger.info(f"Recovered and switched to API key {status.key[:8]}... (index {i})")
                return status.key
        
        logger.error("No available API keys found. All keys are in cooldown.")
        return None
    
    def mark_key_quota_error(self, api_key: str) -> bool:
        """
        Mark an API key as having hit a quota error.
        
        Args:
            api_key: The API key that hit the quota error
            
        Returns:
            True if another key is available, False if all keys are exhausted
        """
        for status in self.key_statuses:
            if status.key == api_key:
                status.mark_quota_error(self.cooldown_minutes)
                break
        
        # Try to get another available key
        return self.get_available_key() is not None
    
    def _check_cooldown_recovery(self):
        """Check and recover keys from cooldown if their time has passed."""
        current_time = datetime.now()
        for status in self.key_statuses:
            if not status.is_active and status.cooldown_until and current_time >= status.cooldown_until:
                status.reset_errors()
                logger.info(f"API key {status.key[:8]}... recovered from cooldown")
    
    def is_quota_error(self, error: Exception) -> bool:
        """
        Determine if an error is related to quota/rate limiting.
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error is quota-related
        """
        error_str = str(error).lower()
        logger.debug(f"Checking if error is quota-related: {error_str}")
        quota_indicators = [
            "quota exceeded",
            "rate limit",
            "quota",
            "limit exceeded",
            "too many requests",
            "resource exhausted",
            "429",
            "quota_exceeded",
            "rate_limit_exceeded",
            # OpenAI specific errors
            "insufficient_quota",
            "billing_hard_limit_reached",
            "tokens_exceeded"
        ]
        
        return any(indicator in error_str for indicator in quota_indicators)
    
    def is_other_error(self, error: Exception) -> bool:
        """
        Determine if an error is related to other issues (not quota-related).
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error is other (not quota-related)
        """
        error_str = str(error).lower()
        logger.debug(f"Checking if error is other (not quota-related): {error_str}")
        other_indicators = [
            "internal error",
            "api limit reached",
            "500",
            "InternalServerError",
            "retry",
            "service unavailable",
            "ServiceUnavailable",
            "503",
            "quota exceeded for this key"
        ]
        
        return any(indicator in error_str for indicator in other_indicators)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of all API key statuses."""
        active_count = sum(1 for status in self.key_statuses if status.is_active and not status.is_in_cooldown())
        in_cooldown_count = sum(1 for status in self.key_statuses if status.is_in_cooldown())
        total_errors = sum(status.error_count for status in self.key_statuses)
        
        return {
            "total_keys": len(self.key_statuses),
            "active_keys": active_count,
            "keys_in_cooldown": in_cooldown_count,
            "current_key_index": self.current_index,
            "current_key_preview": self.key_statuses[self.current_index].key[:8] + "...",
            "total_quota_errors": total_errors,
            "key_details": [
                {
                    "index": i,
                    "key_preview": status.key[:8] + "...",
                    "is_active": status.is_active,
                    "in_cooldown": status.is_in_cooldown(),
                    "error_count": status.error_count,
                    "cooldown_until": status.cooldown_until.isoformat() if status.cooldown_until else None
                }
                for i, status in enumerate(self.key_statuses)
            ]
        }
