"""
Base extractor module for A-MINT.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass
from ..models.pricing import PricingData

@dataclass
class BaseExtractor(ABC):
    """Base extractor interface for A-MINT."""
    
    html: str
    saas_name: str
    
    def __post_init__(self):
        """Initialize the base extractor."""
    
    @abstractmethod
    def extract(self) -> PricingData:
        """Extract pricing data from the provided HTML content.
        
        Returns:
            A PricingData object containing the extracted data.
        """
        pass
    
    @abstractmethod
    def extract_plans(self) -> Dict[str, Any]:
        """Extract pricing plans from the HTML content.
        
        Returns:
            A dictionary containing the extracted plans and configuration.
        """
        pass
    
    @abstractmethod
    def extract_features(self) -> List[Dict[str, Any]]:
        """Extract features from the HTML content.
        
        Returns:
            A list of dictionaries containing the extracted features.
        """
        pass
    
    @abstractmethod
    def extract_add_ons(self) -> Dict[str, Any]:
        """Extract add-ons from the HTML content.
        
        Returns:
            A dictionary containing the extracted add-ons.
        """
        pass