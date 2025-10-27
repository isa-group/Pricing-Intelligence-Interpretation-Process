import re
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class NameConverter:
    """Handles name conversion and normalization for different components."""
    
    def to_upper_snake(self, name: str) -> str:
        """Convert to UPPER_SNAKE_CASE format."""
        return re.sub(r'\s+', '_', name.upper())
    
    def to_camel_case(self, name: str) -> str:
        """Convert to camelCase format."""
        intermediate = re.sub(r'[^A-Za-z0-9]+', '_', name)
        lower = intermediate.lower()
        camelized = re.sub(r'_([a-z])', lambda match: match.group(1).upper(), lower)
        return camelized.strip('_')

@dataclass
class NameRegistry:
    """Maintains consistent name mappings for different components."""
    
    converter: NameConverter
    plans: Dict[str, str] = field(default_factory=dict)
    features: Dict[str, str] = field(default_factory=dict)
    usage_limits: Dict[str, str] = field(default_factory=dict)
    add_ons: Dict[str, str] = field(default_factory=dict)
    
    def get_plan_name(self, name: str) -> str:
        """Get normalized plan name."""
        if name not in self.plans:
            self.plans[name] = self.converter.to_upper_snake(name)
        return self.plans[name]
    
    def get_feature_name(self, name: str) -> str:
        """Get normalized feature name."""
        if name not in self.features:
            self.features[name] = self.converter.to_camel_case(name)
        return self.features[name]
    
    def get_usage_limit_name(self, name: str) -> str:
        """Get normalized usage limit name."""
        if name not in self.usage_limits:
            self.usage_limits[name] = self.converter.to_camel_case(name)
        return self.usage_limits[name]
    
    def get_add_on_name(self, name: str) -> str:
        """Get normalized add-on name."""
        if name not in self.add_ons:
            self.add_ons[name] = self.converter.to_upper_snake(name)
        return self.add_ons[name]

@dataclass
class ConfigBuilder:
    """Builds and maintains the configuration structure."""
    
    saas_name: str
    url: str
    names: NameRegistry
    default_plan: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def build_base_config(self) -> Dict[str, Any]:
        """Build the base configuration structure."""
        return {
            'syntaxVersion': "2.1",
            'saasName': self.saas_name,
            'version': "1.0",
            'createdAt': datetime.now().strftime("%Y-%m-%d"),
            'url': self.url
        }
    
    def add_tag(self, tag: str) -> None:
        """Add a tag if it doesn't exist."""
        if tag and tag.strip() and tag not in self.tags:
            self.tags.append(tag.strip())
    
    def get_sorted_tags(self) -> List[str]:
        """Get sorted list of tags."""
        return sorted(self.tags)

class ComponentParser:
    """Base class for parsing different components."""
    
    def __init__(self, names: NameRegistry, config: ConfigBuilder):
        self.names = names
        self.config = config

class PlanParser(ComponentParser):
    """Handles parsing of plan data."""
    
    def parse(self, plans_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse plans data and return structured plans."""
        plans = {}
        raw_plans = plans_data
        
        if raw_plans:
            self.config.default_plan = self.names.get_plan_name(raw_plans[0].get('name', 'DEFAULT'))
            
        for plan in raw_plans:
            raw_plan_name = plan.pop('name', None)
            if raw_plan_name:
                parsed_plan_name = self.names.get_plan_name(raw_plan_name)
                plans[parsed_plan_name] = plan
                plans[parsed_plan_name].setdefault('features', None)
                plans[parsed_plan_name].setdefault('usageLimits', None)
        
        return plans

class FeatureParser(ComponentParser):
    """Handles parsing of feature data."""
    
    def parse(self, features_data: List[Dict[str, Any]], plans: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Parse features data and update plans accordingly."""
        features = {}
        usage_limits = {}
        
        for feature in features_data:
            raw_feature_name = feature.pop('name', None)
            if not raw_feature_name:
                continue
                
            parsed_feature_name = self.names.get_feature_name(raw_feature_name)
            feature_data, usage_limit = self._process_feature(feature, parsed_feature_name, plans)
            features[parsed_feature_name] = feature_data
            if usage_limit:
                usage_limit_name = usage_limit.pop('name')
                usage_limits[usage_limit_name] = usage_limit
                
        
        return features, usage_limits
    
    def _process_feature(self, feature: Dict[str, Any], parsed_name: str, plans: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Process a single feature and update plans."""
        # Process tags
        if 'tag' in feature:
            self.config.add_tag(feature.pop('tag'))
        
        # Process plans
        feature_plans = feature.get('plans', {})
        new_plans = {
            self.names.get_plan_name(plan_key): plan_value
            for plan_key, plan_value in feature_plans.items()
        }
        # Set default value
        if self.config.default_plan and self.config.default_plan in new_plans:
            feature['defaultValue'] = new_plans[self.config.default_plan]
        else:
            first_plan = next(iter(new_plans), None)
            feature['defaultValue'] = new_plans.get(first_plan)
        # Update plans with feature values
        self._update_plans_with_feature(parsed_name, feature, new_plans, plans)
            
        # Process usage limits
        usage_limit = None
        if 'limit' in feature:
            usage_limit = self._process_usage_limit(feature, plans)
        
        feature.pop('plans', None)
        return feature, usage_limit
    
    def _update_plans_with_feature(self, feature_name: str, feature: Dict[str, Any], 
                                 feature_plans: Dict[str, Any], plans: Dict[str, Any]) -> None:
        """Update plans with feature values."""
        default_value = feature.get('defaultValue')
        
        for plan_name, plan_value in feature_plans.items():
            if plan_value != default_value:
                if 'features' not in plans[plan_name] or plans[plan_name]['features'] is None:
                    plans[plan_name]['features'] = {}
                plans[plan_name]['features'][feature_name] = {
                    'value': plan_value if plan_value != ".inf" else float("inf")
                }
    
    def _process_usage_limit(self, feature: Dict[str, Any], plans: Dict[str, Any]) -> Dict[str, Any]:
        """Process usage limit for a feature."""
        limit = feature.pop('limit', {})
        if not limit:
            return None
        limit_name = limit.pop('name', None)
        if not limit_name:
            return None
        
        normalized_plans = {}
        if 'plans' in limit and isinstance(limit['plans'], dict):
            for plan_key, plan_data in limit['plans'].items():
                if isinstance(plan_data, dict):
                    normalized_plans[plan_key] = plan_data
                else:
                    normalized_plans[plan_key] = {'limitValue': plan_data}
            limit['plans'] = normalized_plans
            
        parsed_limit_name = self.names.get_usage_limit_name(limit_name)
        
        usage_limit = {}
        usage_limit['name'] = parsed_limit_name
        usage_limit.update(limit)
        
        if self.config.default_plan and self.config.default_plan in usage_limit['plans']:
            usage_limit['defaultValue'] = usage_limit['plans'][self.config.default_plan]['limitValue']
        else:
            first_plan = next(iter(usage_limit['plans']), None)
            usage_limit['defaultValue'] = usage_limit['plans'][first_plan]['limitValue']
            
        self._update_plans_with_usage_limit(parsed_limit_name, limit, plans, usage_limit['defaultValue'])
        
        if usage_limit['defaultValue'] == ".inf":
            usage_limit['defaultValue'] = float("inf")
            
        new_linked_features = []
        for linked_feature in usage_limit['linkedFeatures']:
            parsed_linked_feature = self.names.get_feature_name(linked_feature)
            new_linked_features.append(parsed_linked_feature)
            
        usage_limit['linkedFeatures'] = new_linked_features
        usage_limit.pop('plans', None)
        
        return usage_limit
    
    def _update_plans_with_usage_limit(self, limit_name: str, limit: Dict[str, Any], 
                                     plans: Dict[str, Any], limit_default_value: str) -> None:
        """Update plans with usage limit values."""
        limit_plans = limit.get('plans', {})
        
        for plan_name, plan_data in limit_plans.items():
            new_plan_name = self.names.get_plan_name(plan_name)
            if plan_data:
                if plan_data.get('limitValue') == limit_default_value:
                    continue
                if 'usageLimits' not in plans[new_plan_name] or plans[new_plan_name]['usageLimits'] is None:
                    plans[new_plan_name]['usageLimits'] = {}
                plans[new_plan_name]['usageLimits'][limit_name] = {
                    'limitValue': plan_data.get('limitValue') if plan_data.get('limitValue') != ".inf" else float("inf")
                }

class AddOnParser(ComponentParser):
    """Handles parsing of add-on data."""
    
    def parse(self, add_ons_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse add-ons data."""
        add_ons = {}
        
        for add_on in add_ons_data.get('add-ons', []):
            raw_add_on_name = add_on.pop('name', None)
            if not raw_add_on_name:
                continue
                
            parsed_add_on_name = self.names.get_add_on_name(raw_add_on_name)
            add_ons[parsed_add_on_name] = self._process_add_on(add_on)
        
        return add_ons
    
    def _process_add_on(self, add_on: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single add-on."""
        # Process plan references
        if 'availableForPlans' in add_on:
            add_on['availableFor'] = [
                self.names.get_plan_name(ref) for ref in add_on['availableForPlans']
            ]
        
        add_on.pop('availableForPlans', None)
        
        if 'dependsOnAddOns' in add_on:
            add_on['dependsOn'] = [
                self.names.get_add_on_name(ref) for ref in add_on['dependsOnAddOns']
            ]
        
        add_on.pop('dependsOnAddOns', None)
        
        if 'excludeAddOns' in add_on:
            add_on['excludes'] = [
                self.names.get_add_on_name(ref) for ref in add_on['excludeAddOns']
            ]
        
        add_on.pop('excludeAddOns', None)
        
        # Process features
        if 'features' in add_on:
            add_on['features'] = {
                self.names.get_feature_name(k): {'value': v} if not isinstance(v, dict) else v
                for k, v in dict(add_on['features']).items()
            }
            
            if add_on['features'] == {}:
                add_on['features'] = None
        
        # Process usage limits
        if 'usageLimits' in add_on and add_on['usageLimits']:
            raw_limits = add_on.get('usageLimits', []) or []
            normal_limits = {}
            extend_limits = {}

            for item in raw_limits:
                # 1) extract the limit name
                limit_name = item.pop('name', None)
                if not limit_name:
                    continue

                # 2) everything else in `item` is the content
                content = item.copy()  # {'limitValueType':..., 'limitValue':..., ...}

                # 3) pull off the extend flag
                extend_flag = content.pop('extendPreviousOne', False)

                # 4) normalize the numeric value
                value = content.pop('limitValue', None)
                content['value'] = float('inf') if value == '.inf' else value

                # 5) drop unused fields
                content.pop('limitValueType', None)
                content.pop('limitUnit', None)

                # 6) map to your normalized key
                key = self.names.get_usage_limit_name(limit_name)

                # 7) put it in the right bucket
                if extend_flag:
                    extend_limits[key] = content
                else:
                    normal_limits[key] = content

            add_on['usageLimits'] = normal_limits or None
            add_on['usageLimitsExtensions'] = extend_limits or None

        else:
            add_on['usageLimits'] = None
            add_on['usageLimitsExtensions'] = None
        return add_on

class YAMLSerializer:
    """Class for handling YAML serialization, deserialization, and JSON to YAML conversion."""
    
    def __init__(self, saas_name: str = "", url: str = ""):
        """Initialize the YAMLSerializer with optional metadata."""
        self.name_converter = NameConverter()
        self.name_registry = NameRegistry(self.name_converter)
        self.config_builder = ConfigBuilder(saas_name, url, self.name_registry)
        
        self.plan_parser = PlanParser(self.name_registry, self.config_builder)
        self.feature_parser = FeatureParser(self.name_registry, self.config_builder)
        self.add_on_parser = AddOnParser(self.name_registry, self.config_builder)
    
    @staticmethod
    def serialize(data: Dict[str, Any]) -> str:
        """Serialize a dictionary to YAML format."""
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    @staticmethod
    def deserialize(yaml_str: str) -> Dict[str, Any]:
        """Deserialize a YAML string to a dictionary."""
        return yaml.safe_load(yaml_str)
    
    @staticmethod
    def validate_yaml(yaml_str: str) -> bool:
        """Validate YAML string."""
        try:
            yaml.safe_load(yaml_str)
            return True
        except yaml.YAMLError:
            return False

    def from_json(self, plans: List[Dict[str, Any]], features: List[Dict[str, Any]], 
                 add_ons: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert JSON data to YAML format."""
        # Parse components
        parsed_plans = self.plan_parser.parse(plans)
        parsed_features, parsed_usage_limits = self.feature_parser.parse(features, parsed_plans)
        parsed_add_ons = self.add_on_parser.parse(add_ons or {})
        
        # Build final config
        final_config = self.config_builder.build_base_config()
        final_config.update(add_ons.get('config', {}))
        
        if self.config_builder.tags:
            final_config['tags'] = self.config_builder.get_sorted_tags()
        if parsed_features:
            final_config['features'] = parsed_features
        if parsed_usage_limits:
            final_config['usageLimits'] = parsed_usage_limits
        if parsed_plans:
            final_config['plans'] = parsed_plans
        if parsed_add_ons:
            final_config['addOns'] = parsed_add_ons

        
        return final_config 