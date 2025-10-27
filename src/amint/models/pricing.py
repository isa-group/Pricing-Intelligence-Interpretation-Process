"""
Pricing data models for A-MINT.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class PricingData:
    """Represents the complete pricing data for a SaaS product."""
    config: Optional[Dict[str, Any]] = None
    plans: List[Dict[str, Any]] = field(default_factory=list)
    features: List[Dict[str, Any]] = field(default_factory=list)
    add_ons: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the pricing data to a dictionary."""
        return {
            "config": self.config or {},
            "plans": self.plans,
            "features": self.features,
            "add_ons": self.add_ons
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PricingData':
        """Create a PricingData instance from a dictionary."""
        return cls(
            config=data.get("config"),
            plans=data.get("plans", []),
            features=data.get("features", []),
            add_ons=data.get("add_ons", [])
        ) 