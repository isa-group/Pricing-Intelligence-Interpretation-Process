"""
Base AI client interface for A-MINT.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

@dataclass
class AIConfig:
    """Base configuration for AI clients."""
    model: str
    api_key: Optional[str] = None
    api_keys: Optional[List[str]] = None  # Multiple API keys for rotation
    max_retries: int = 5
    retry_delay: int = 60
    temperature: float = 0.7
    key_cooldown_minutes: int = 2  # Cooldown period for quota-limited keys
    base_url: Optional[str] = None  # Custom endpoint URL for OpenAI-compatible APIs
    better_model: Optional[str] = None  # Model for better quality responses

class AIClient(ABC):
    """Base interface for AI clients."""
    
    def __init__(self, config: AIConfig):
        """
        Initialize the AI client.
        
        Args:
            config: The client configuration
        """
        self.config = config
        self._configure()
    
    @abstractmethod
    def _configure(self) -> None:
        """Configure the AI client."""
        pass
    
    @abstractmethod
    def _make_request(
        self,
        prompt: str,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Make a request to the AI service.
        
        Args:
            prompt: The prompt to generate content from
            generation_config: Optional generation configuration
            
        Returns:
            The generated content
            
        Raises:
            Exception: If the request fails after max retries
        """
        pass
    
    @abstractmethod
    def make_full_request(
        self,
        initial_prompt: str,
        max_tries: int = 5
    ) -> str:
        """
        Make a complete request, handling truncation.
        
        Args:
            initial_prompt: The initial prompt to send
            max_tries: Maximum number of attempts to get complete JSON
            
        Returns:
            A complete JSON string
            
        Raises:
            ValueError: If valid JSON cannot be formed after max tries
        """
        pass
    
    @abstractmethod
    def _build_continue_prompt(self, initial_prompt: str, accumulated_text: str) -> str:
        """Build a prompt to continue generating JSON."""
        pass
    
    @abstractmethod
    def _process_response_chunk(self, response: str, accumulated_text: str) -> str:
        """Process a response chunk, handling boundaries."""
        pass
    
    @abstractmethod
    def _parse_response(self, response: str) -> str:
        """Parse the response, handling code blocks."""
        pass 