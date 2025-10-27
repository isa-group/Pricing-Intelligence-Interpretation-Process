"""
AI module for A-MINT.
Contains AI client implementations for various providers.
"""

from .base import AIClient, AIConfig
from .openai_api import OpenAIAPI
from .api_key_manager import APIKeyManager

__all__ = [
    "AIClient",
    "AIConfig", 
    "OpenAIAPI",  # Now the primary client
    "APIKeyManager",
    "DefaultAIClient",  # Alias for OpenAIAPI
    "create_default_gemini_config"  # Helper function
]

# Default AI client for the project (now using OpenAI-compatible API)
DefaultAIClient = OpenAIAPI

# Default configuration for Gemini models via OpenAI API
def create_default_gemini_config(**kwargs) -> AIConfig:
    """
    Create a default configuration for Gemini models using OpenAI-compatible API.
    
    Args:
        **kwargs: Additional configuration parameters to override defaults
        
    Returns:
        AIConfig configured for Gemini via OpenAI API
    """
    default_config = {
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "temperature": 0.0,
        "better_model": "gemini-2.5-pro",
    }
    default_config.update(kwargs)
    return AIConfig(**default_config)