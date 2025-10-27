"""
Data extraction module for A-MINT.
"""
import json
import logging
import copy
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
from bs4 import BeautifulSoup
import traceback, os, re
from soupsieve import SelectorSyntaxError

from ..ai.base import AIClient, AIConfig
from .base import BaseExtractor
from ..models.pricing import PricingData

logger = logging.getLogger(__name__)

@dataclass
class ExtractionConfig:
    """Configuration for data extraction."""
    use_html_context: bool = True
    ai_client: Optional[AIClient] = None

@dataclass
class ExtractionResult:
    """Result of a data extraction operation."""
    plans: Dict[str, Any] = field(default_factory=dict)
    features: List[Dict[str, Any]] = field(default_factory=list)
    add_ons: Dict[str, Any] = field(default_factory=dict)
    html_context: Optional[str] = None

@dataclass
class ExtractData(BaseExtractor):
    """Extracts pricing data from SaaS websites using AI."""
    
    config: ExtractionConfig = field(default_factory=ExtractionConfig)
    plans: Dict[str, Any] = field(default_factory=dict)
    features: List[Dict[str, Any]] = field(default_factory=list)
    add_ons: Dict[str, Any] = field(default_factory=dict)
    prompts: Dict[str, str] = field(default_factory=dict)
    soup: BeautifulSoup = field(init=False)
    
    def __post_init__(self):
        """Initialize the extractor."""
        super().__post_init__()
        self.soup = BeautifulSoup(self.html, 'lxml')
        if not self.config.ai_client:
            # Default to OpenAI API with Gemini models if no client provided
            from ..ai import OpenAIAPI, create_default_gemini_config
            ai_config = create_default_gemini_config()
            self.config.ai_client = OpenAIAPI(ai_config)
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self._load_prompts()
    
    def _load_prompts(self) -> None:
        """Load prompt templates from the prompts directory and escape curly braces except for placeholders."""
        def escape_braces(text, placeholders):
            import re
            # Escape all braces
            text = text.replace('{', '{{').replace('}', '}}')
            # Unescape placeholders
            for ph in placeholders:
                text = text.replace('{{' + ph + '}}', '{' + ph + '}')
            return text

        # Define known placeholders for each prompt type
        prompt_placeholders = {
            'plans_container': ['saas_name', 'html'],
            'plans_to_markdown': ['saas_name', 'html'],
            'plans_parse': ['saas_name', 'markdown'],
            'features_container': ['saas_name', 'html'],
            'features_to_markdown': ['saas_name', 'html'],
            'features_validate_markdown': ['saas_name', 'html', 'markdown', 'plans'],
            'features_parse': ['saas_name', 'markdown', 'plans'],
            'features_validate': ['saas_name', 'features_json', 'plans'],
            'add_ons_container': ['saas_name', 'html'],
            'add_ons_to_markdown': ['saas_name', 'html'],
            'add_ons_parse': ['saas_name', 'markdown', 'config', 'features', 'plans'],
            'add_ons_validate': ['saas_name', 'json'],
            'add_ons_overage': ['saas_name', 'html', 'features', 'config', 'add_ons', 'plans'],
            'html_to_markdown': ['saas_name', 'html'],
            'html_validate_markdown': ['saas_name', 'markdown', 'html'],
            'html_system': [],
        }
        for category in ["plans", "features", "add_ons", "html"]:
            category_dir = self.prompts_dir / category
            if category_dir.exists():
                for prompt_file in category_dir.glob("*.md"):
                    prompt_type = prompt_file.stem
                    with open(prompt_file, "r") as f:
                        raw = f.read()
                        key = f"{category}_{prompt_type}"
                        placeholders = prompt_placeholders.get(key, [])
                        self.prompts[key] = escape_braces(raw, placeholders)

    def _get_prompt(self, category: str, prompt_type: str) -> str:
        """Get a prompt template.
        
        Args:
            category: The category of the prompt (e.g., 'plans', 'features', 'add_ons').
            prompt_type: The type of the prompt (e.g., 'container', 'parse', 'validate').
            
        Returns:
            The prompt template.
            
        Raises:
            ValueError: If the prompt template is not found.
        """
        prompt_key = f"{category}_{prompt_type}"
        if prompt_key not in self.prompts:
            raise ValueError(f"Prompt template not found: {prompt_key}")
        return self.prompts[prompt_key]

    def _normalize_markdown_dashes(self, md_text: str, 
                        max_table_dashes: int = 50, 
                        non_table_dash_limit: int = 3) -> str:
        """
        1) In Markdown table separator rows (lines containing '|'), clamp any sequence
        of more than `max_table_dashes` hyphens (with optional leading/trailing colons)
        down to exactly `max_table_dashes`.
        2) In non-table lines, collapse any run of 4 or more hyphens into exactly
        `non_table_dash_limit` hyphens (e.g. '----' → '---').
        """
        # Pattern for table lines: optional ':' prefix, > max_table_dashes hyphens, optional ':' suffix
        table_pattern = re.compile(
            rf"(?P<prefix>:?)(?P<dashes>-{{{max_table_dashes+1},}})(?P<suffix>:?)"
        )

        def clamp_table(match):
            """
            Clamp the dashes in a table line to exactly `max_table_dashes`.
            """
            return f"{match.group('prefix')}{'-' * max_table_dashes}{match.group('suffix')}"

        # Pattern for non-table lines: any run of 4 or more hyphens
        non_table_pattern = re.compile(r'-{4,}')

        out_lines = []
        for line in md_text.splitlines(keepends=True):
            if '|' in line:
                # Clamp only in table-like lines
                new_line = table_pattern.sub(clamp_table, line)
            else:
                # Collapse long dash runs in non-table lines
                new_line = non_table_pattern.sub('-' * non_table_dash_limit, line)
            out_lines.append(new_line)

        return ''.join(out_lines).strip()

    def extract(self, *, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> PricingData:
        """Extract pricing data from the provided HTML content."""
        try:
            logging.info(f"Extracting data from the SaaS using the client '{self.config.ai_client.__class__.__name__}'")
            
            self.html_markdown = self.parse_html_to_markdown(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
            
            self.html_markdown = self._normalize_markdown_dashes(self.html_markdown)
        
            new_markdown = self.validate_html_markdown(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
            
            if not new_markdown:
                logging.error("No Markdown content returned from validation.")
            else:
                logging.info(f"HTML Markdown changed: {self.html_markdown.strip() != new_markdown.strip()}")    
                self.html_markdown = new_markdown

            self.html_markdown = self._normalize_markdown_dashes(self.html_markdown)

            if not self.html_markdown:
                raise ValueError("No Markdown content extracted from the HTML.")
            
            # Extract the pricing plans
            self.plans = self.extract_plans(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)

            # Extract the features and usage limits
            self.features = self.extract_features(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
            
            # # Validate the extracted features and usage limits
            # if self.features:
            #     self.features = self._validate_features_and_usage_limits(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
            #     logging.info(f"Validated Features JSON:\n {json.dumps(self.features, indent=2)}")
            
            # features_validated = copy.deepcopy(self.features)

            # Extract the add-ons and update features if necessary
            self.add_ons = self.extract_add_ons(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
            first_add_ons_features = self.add_ons.get("features", [])

            # Extract the add-ons that model overage costs and similar
            self.add_ons = self._update_overage_add_ons(self.features, self.add_ons, self.plans, transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
            logging.info(f"Final Add-Ons JSON (with overage costs): {json.dumps(self.add_ons, indent=2)}")
            
            # Update the features list with add-ons-specific features
            add_ons_features = self.add_ons.pop("features", [])
            self.features.extend(add_ons_features)

            # Add any new features from the add-ons that were neither already in the original features list nor in the overage add-ons features list
            for feature in first_add_ons_features:
                if feature not in self.features:
                    self.features.append(feature)
            
            # Validate the extracted features and usage limits again
            # if self.features and features_validated != self.features:
            if self.features:
                old_features = copy.deepcopy(self.features)
                self.features = self._validate_features_and_usage_limits(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
                logging.info(f"Validated Features JSON (with add-ons): {json.dumps(self.features, indent=2)}")
                if self.features != old_features:
                    logging.info("Features changed after validation.")
                else:
                    logging.info("Features remained the same after validation.")

            return PricingData(
                config=self.plans.get("config"),
                plans=self.plans.get("plans", []),
                features=self.features,
                add_ons=self.add_ons
            )
        except Exception as e:
            logger.error(f"Exception in extract: {str(e)}\n{traceback.format_exc()}")
            raise
        
    def parse_html_to_markdown(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> str:
        """
        Converts the HTML content to Markdown format using the AI client.
        
        Args:
            transformation_call_id: Optional transformation call ID for tracking.
            llm_call_ids: Optional list of LLM call IDs for tracking.
            endpoint: Optional endpoint for the AI client.
            
        Returns:
            The converted Markdown content.
        """
        if not self.config.ai_client:
            raise ValueError("AI client not configured")
        
        prompt = self._get_prompt("html", "to_markdown").format(
            saas_name=self.saas_name,
            html=self.html
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="convert_html_to_markdown",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids,
            json_output=False  # We want the raw Markdown response, not JSON
        )
        
        # Remove markdown code blocks if present
        if response.startswith('```'):
            response = response.split('```')[1].strip()
        if response.endswith('```'):
            response = response[:-3].strip()
        
        logging.info("Converted HTML to Markdown")
        logging.info(response)
        return response

    def validate_html_markdown(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> str:
        """
        Validates and improves the extracted Markdown content.
        """
        if not self.config.ai_client:
            raise ValueError("AI client not configured")

        prompt = self._get_prompt("html", "validate_markdown").format(
            saas_name=self.saas_name,
            markdown=self.html_markdown,
            html=self.html
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="validate_markdown",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids,
            json_output=False
        )

        logging.info("Validated and improved Markdown")
        logging.info(response)
        return response

    def extract_plans(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> Dict[str, Any]:
        """
        Identifies the container for pricing plans, selects the HTML elements,
        and parses them into the final pricing plans JSON.
        """
        # elements = self._extract_plans_elements(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
        
        plans = self._get_plans(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
        logging.info(f"Final Plans JSON:\n {json.dumps(plans, indent=2)}")
        
        self.plans_names = [plan['name'] for plan in plans.get('plans', [])]
        logger.info(f"Plans names: {self.plans_names}")
        
        return plans

    def _extract_plans_elements(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> List[BeautifulSoup]:
        """
        Identifies the container for pricing plans and selects the HTML elements.
        """
        plans_container = self._get_plans_container(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
        logging.info(f"Containers JSON: {plans_container}")

        elements = self._extract_elements_from_container(plans_container)
        self.plans_elements = elements
        
        # Convert HTML to Markdown
        self.plans_markdown = self._html_to_markdown(elements, "plans", 
                                                    transformation_call_id=transformation_call_id, 
                                                    llm_call_ids=llm_call_ids, 
                                                    endpoint=endpoint)
        logging.info(f"Plans Markdown created")
        
        return elements

    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON object from LLM response, handling code blocks and extra text."""
        import re
        # Remove code block markers if present
        response = response.strip()
        if response.startswith('```'):
            response = re.sub(r'^```[a-zA-Z]*', '', response)
            response = response.strip('`\n')
        # Find the first and last curly braces to extract JSON
        match = re.search(r'({[\s\S]*})', response)
        if match:
            return match.group(1)
        return response

    def _get_plans_container(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> Dict[str, Any]:
        print("_get_plans_container called - DEBUG")
        """
        Asks the AI client to identify containers in the HTML
        that hold pricing plan information.
        """
        prompt = self._get_prompt("plans", "container").format(
            saas_name=self.saas_name,
            html=self.html
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="get_plans_container",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids
        )
        logger.info(f"Raw AI response for plans container: {response}")
        print(f"Raw AI response for plans container: {response}")
        response = self._extract_json_from_response(response)
        try:
            selectors_json = json.loads(response)
            if isinstance(selectors_json, dict) and "selectors" in selectors_json:
                return selectors_json
            else:
                logger.error(f"_get_plans_container: Response is not in the expected JSON format: {response}")
                raise ValueError("Response is not in the expected JSON format.")
        except json.JSONDecodeError as e:
            logger.error(f"_get_plans_container: JSONDecodeError: {str(e)}\nResponse: {response}\n{traceback.format_exc()}")
            raise ValueError("The response is not a valid JSON object.")

    def _get_plans(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> Dict[str, Any]:
        """
        Takes the extracted Markdown for the pricing plans, sends it to the AI client,
        and expects a strictly valid JSON response containing 'config' and 'plans'.
        """
        prompt = self._get_prompt("plans", "parse").format(
            saas_name=self.saas_name,
            markdown=self.html_markdown  # Using Markdown instead of HTML
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="get_plans",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids
        )

        try:
            plans_json = json.loads(response)
            if isinstance(plans_json, dict) and "plans" in plans_json:
                return plans_json
            else:
                raise ValueError("Response is not in the expected JSON format.")
        except json.JSONDecodeError:
            raise ValueError("The response is not a valid JSON object.")
    
    def extract_features(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> List[Dict[str, Any]]:
        """
        Identifies the container for features, selects the HTML elements,
        and parses them into the final features JSON.
        """
        # elements = self._extract_features_elements(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)

        features = self._get_features(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
        logging.info(f"Final Features JSON:\n {json.dumps(features, indent=2)}")
        return features

    def _extract_features_elements(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> List[BeautifulSoup]:
        """
        Identifies the container for features and selects the HTML elements.
        """
        features_container = self._get_features_container(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
        logging.info(f"Containers JSON: {features_container}")

        elements = self._extract_elements_from_container(features_container)
        self.features_elements = elements
        
        # Convert HTML to Markdown
        self.features_markdown = self._html_to_markdown(elements, "features", 
                                                       transformation_call_id=transformation_call_id, 
                                                       llm_call_ids=llm_call_ids, 
                                                       endpoint=endpoint)
        logging.info(f"Features Markdown created")
        
        # Validate the Markdown
        self.features_markdown = self._validate_features_markdown(self.features_markdown,
                                                                 transformation_call_id=transformation_call_id, 
                                                                 llm_call_ids=llm_call_ids, 
                                                                 endpoint=endpoint)
        logging.info(f"Features Markdown validated")
        
        return elements

    def _get_features_container(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> Dict[str, Any]:
        """
        Asks the AI client to identify containers in the HTML
        that hold feature information.
        """
        prompt = self._get_prompt("features", "container").format(
            saas_name=self.saas_name,
            html=self.html
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="get_features_container",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids
        )
        logger.info(f"Raw AI response for features container: {response}")
        print(f"Raw AI response for features container: {response}")
        response = self._extract_json_from_response(response)
        try:
            selectors_json = json.loads(response)
            if isinstance(selectors_json, dict) and "selectors" in selectors_json:
                return selectors_json
            else:
                raise ValueError("Response is not in the expected JSON format.")
        except json.JSONDecodeError:
            raise ValueError("The response is not a valid JSON object.")

    def _get_features(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> List[Dict[str, Any]]:
        """
        Takes the extracted Markdown for the features, sends it to the AI client,
        and expects a strictly valid JSON response containing an array of feature objects.
        """
        prompt = self._get_prompt("features", "parse").format(
            saas_name=self.saas_name,
            markdown=self.html_markdown,  # Using Markdown instead of HTML
            plans=self.plans_names
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="get_features",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids
        )

        try:
            features_json = json.loads(response)
            if isinstance(features_json, list):
                return features_json
            else:
                raise ValueError("Response is not in the expected JSON format.")
        except json.JSONDecodeError:
            raise ValueError("The response is not a valid JSON object.")
    
    def extract_add_ons(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> Dict[str, Any]:
        """
        Identifies the container for add-ons, selects the HTML elements,
        and parses them into the final add-ons JSON.
        """
        # elements = self._extract_add_ons_elements(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
        
        add_ons = self._get_add_ons(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
        logging.info(f"Final Add-ons JSON:\n {json.dumps(add_ons, indent=2)}")
        return add_ons

    def _extract_add_ons_elements(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> List[BeautifulSoup]:
        """
        Identifies the container for add-ons and selects the HTML elements.
        """
        add_ons_container = self._get_add_ons_container(transformation_call_id=transformation_call_id, llm_call_ids=llm_call_ids, endpoint=endpoint)
        logging.info(f"Containers JSON: {add_ons_container}")

        elements = self._extract_elements_from_container(add_ons_container)
        self.add_ons_elements = elements
        
        # Convert HTML to Markdown
        self.add_ons_markdown = self._html_to_markdown(elements, "add_ons", 
                                                      transformation_call_id=transformation_call_id, 
                                                      llm_call_ids=llm_call_ids, 
                                                      endpoint=endpoint)
        logging.info(f"Add-ons Markdown created")
        
        return elements

    def _get_add_ons_container(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> Dict[str, Any]:
        """
        Asks the AI client to identify containers in the HTML
        that hold add-on information.
        """
        prompt = self._get_prompt("add_ons", "container").format(
            saas_name=self.saas_name,
            html=self.html
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="get_add_ons_container",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids
        )
        logger.info(f"Raw AI response for add-ons container: {response}")
        print(f"Raw AI response for add-ons container: {response}")
        response = self._extract_json_from_response(response)
        try:
            selectors_json = json.loads(response)
            if isinstance(selectors_json, dict) and "selectors" in selectors_json:
                return selectors_json
            else:
                raise ValueError("Response is not in the expected JSON format.")
        except json.JSONDecodeError:
            raise ValueError("The response is not a valid JSON object.")

    def _get_add_ons(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> Dict[str, Any]:
        """
        Takes the extracted Markdown for the add-ons, sends it to the AI client,
        and expects a strictly valid JSON response containing an array of add-on objects.
        """
        prompt = self._get_prompt("add_ons", "parse").format(
            saas_name=self.saas_name,
            markdown=self.html_markdown,  # Using Markdown instead of HTML
            plans=self.plans_names,
            config=json.dumps(self.plans.get("config", {}), indent=2),
            features=json.dumps(self.features, indent=2)
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="get_add_ons",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids
        )

        try:
            add_ons_json = json.loads(response)
            if isinstance(add_ons_json, dict):
                return add_ons_json
            else:
                raise ValueError("Response is not in the expected JSON format.")
        except json.JSONDecodeError:
            raise ValueError("The response is not a valid JSON object.")
    
    def _validate_features_and_usage_limits(self, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> List[Dict[str, Any]]:
        """Validate features and usage limits."""
        if not self.config.ai_client:
            raise ValueError("AI client not configured")
        
        # Build prompt for validation
        prompt = self._get_prompt("features", "validate").format(
            saas_name=self.saas_name,
            features_json=json.dumps(self.features, indent=2),
            plans=self.plans_names
        )
        
        # Get AI response
        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="validate_features_and_usage_limits",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids
        )
        data = json.loads(response)
        
        return data
    
    def _validate_features_markdown(self, markdown: str, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> str:
        """Validate features markdown data before parsing."""
        if not self.config.ai_client:
            raise ValueError("AI client not configured")
        
        # Convertir elementos HTML a string para el prompt
        combined_elements = "\n".join([str(el) for el in self.features_elements])
        
        # Build prompt for validation
        prompt = self._get_prompt("features", "validate_markdown").format(
            saas_name=self.saas_name,
            markdown=markdown,
            plans=self.plans_names,
            html=combined_elements
        )
        
        # Get AI response
        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="validate_features_markdown",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids,
            json_output=False  # We want the raw Markdown response, not JSON
        )
        
        # Remove markdown code blocks if present
        if response.startswith('```'):
            response = response.split('```')[1].strip()
        if response.endswith('```'):
            response = response[:-3].strip()
            
        logging.info("Validated Features Markdown")
        logging.info(response)
        return response
    
    def _get_html_context(self) -> Optional[str]:
        """Get formatted HTML context for AI processing."""
        if not self.config.use_html_context:
            return None
            
        plans_elements = self.extract_plans_elements()
        features_elements = self.extract_features_elements()
        add_ons_elements = self.extract_add_ons_elements()
        
        return f"""
        <!-- Plans-related HTML elements -->
        <div id="plans">
            {plans_elements}
        </div>
        <!-- Features-related HTML elements -->
        <div id="features">
            {features_elements}
        </div>
        <!-- Add-ons-related HTML elements -->
        <div id="add_ons">
            {add_ons_elements}
        </div>
        """

    def _extract_elements_from_container(self, container: Dict[str, Any]) -> List[BeautifulSoup]:
        """
        Given a container dict with 'selectors' and 'elements', extract and return all matching elements.
        - Tries each CSS selector; on SelectorSyntaxError, falls back to basic tag+class lookup.
        - Strips complex pseudo-classes, attribute, and combinators for fallback.
        - Handles explicit 'elements': [{'tag': ..., 'attributes': {...}}].
        - Removes duplicates while preserving document order.
        """
        collected: List[BeautifulSoup] = []
        seen: Set[int] = set()

        def fallback_by_tag_and_classes(raw_selector: str) -> List[BeautifulSoup]:
            # Remove everything after first pseudo, attribute or combinator
            simple = re.split(r'[:\[>\s]', raw_selector.strip())[0]
            tag_match = re.match(r'^([a-zA-Z0-9_]+)', simple)
            tag = tag_match.group(1) if tag_match else None
            # collect class tokens
            class_names = re.findall(r'\.([^.\[\]:>#\s]+)', raw_selector)
            if class_names:
                # find_all supports only single class or list matches ANY class; filter manually
                results = self.soup.find_all(tag or True)
                filtered = [el for el in results if el.has_attr('class') and all(c in el['class'] for c in class_names)]
                return filtered
            return []

        # 1) CSS selectors
        for selector in container.get('selectors', []):
            try:
                found = self.soup.select(selector)
            except SelectorSyntaxError:
                found = fallback_by_tag_and_classes(selector)

            for el in found:
                uid = id(el)
                if uid not in seen:
                    seen.add(uid)
                    collected.append(el)

        # 2) Explicit element dicts
        for element in container.get('elements', []):
            tag = element.get('tag') or True
            attrs = element.get('attributes', {})
            found = self.soup.find_all(tag, attrs=attrs)
            for el in found:
                uid = id(el)
                if uid not in seen:
                    seen.add(uid)
                    collected.append(el)

        return collected

    
    def _update_overage_add_ons(
        self,
        features: List[Dict[str, Any]],
        add_ons: Dict[str, Any],
        plans: Dict[str, Any],
        transformation_call_id=None,
        llm_call_ids=None,
        endpoint=None
    ) -> Dict[str, Any]:
        """Update add-ons with overage costs.
        
        Args:
            features: List of existing features
            add_ons: Dictionary containing existing add-ons and config
            plans: Dictionary containing plans and their configuration
            
        Returns:
            Dictionary containing updated add-ons, features, and config
        """
        # Get the prompt template and format it with the required data
        prompt = self._get_prompt("add_ons", "overage").format(
            saas_name=self.saas_name,
            html=self.html_markdown,
            features=json.dumps(features, indent=2),
            config=json.dumps(add_ons.get("config", {}), indent=2),
            add_ons=json.dumps(add_ons.get("add-ons", []), indent=2),
            plans=self.plans_names
        )
        
        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function="update_overage_add_ons",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids
        )
        
        try:
            result = json.loads(response)
            # Validate that the response is a JSON object with the required keys
            if not isinstance(result, dict):
                raise ValueError("Response is not a JSON object.")
            for key in ["config", "features", "add-ons"]:
                if key not in result:
                    raise ValueError(f"JSON object is missing the '{key}' key.")
            if not isinstance(result["features"], list):
                raise ValueError("'features' must be a list.")
            if not isinstance(result["add-ons"], list):
                raise ValueError("'add-ons' must be a list.")
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"The response is not a valid JSON object: {e}")
    
    def _html_to_markdown(self, elements: List[BeautifulSoup], category: str, transformation_call_id=None, llm_call_ids=None, endpoint=None) -> str:
        """
        Convert HTML elements to Markdown format using LLM.
        
        Args:
            elements: List of BeautifulSoup elements to convert
            category: Category of elements (plans, features, add_ons)
            
        Returns:
            Markdown representation of the HTML elements
        """
        combined_elements = "\n".join([str(el) for el in elements])
        prompt = self._get_prompt(category, "to_markdown").format(
            saas_name=self.saas_name,
            html=combined_elements
        )

        response = self.config.ai_client.make_full_request(
            prompt,
            endpoint=endpoint,
            function=f"convert_{category}_to_markdown",
            transformation_call_id=transformation_call_id,
            llm_call_ids=llm_call_ids,
            json_output=False  # We want the raw Markdown response, not JSON
        )
        
        # Remove markdown code blocks if present
        if response.startswith('```'):
            response = response.split('```')[1].strip()
        if response.endswith('```'):
            response = response[:-3].strip()
        
        logging.info(f"Converted {category} HTML to Markdown")
        logging.info(response)
        return response