import os
import json
import yaml
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from ..ai.base import AIConfig
import time

NO_SPECIFIC_ERROR_DETAILS = "No specific error details provided."

class CSPEndpointError(Exception):
    """Exception raised for errors related to CSP endpoints."""
    pass

class FixYaml:
    """
    Handles YAML validation and automated fixes via the OpenAI-compatible API and a CSP Validator endpoint.
    Modular, decoupled, and aligned with the codebase's best practices.
    """
    def __init__(
        self,
        file_path: str,
        url: Optional[str] = None,
        max_retries: int = 50,
        use_html_context: bool = True,
        html_data: Optional[Dict[str, Any]] = None,
        ai_client: Optional[AIConfig] = None,
        prompts_dir: str = "src/amint/prompts/fix_yaml",
        transformation_call_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        llm_call_ids: Optional[list] = None
    ):
        self.is_valid = False
        self.file_path = file_path
        self.validator_endpoint = os.getenv('ANALYSIS_API', "http://localhost:8002/api/v1")
        if not self.validator_endpoint:
            raise ValueError('YAML Validator Endpoint not found!')
        self.finish = False
        self.max_retries = max_retries
        self.counter = 0
        self.prompts_dir = Path(prompts_dir)
        self.prompts = self._load_prompts()
        self.ai_client = ai_client
        self.transformation_call_id = transformation_call_id
        self.endpoint = endpoint
        self.llm_call_ids = llm_call_ids if llm_call_ids is not None else []
        self.html = None
        if use_html_context:
            if html_data:
                self.html = html_data
            elif url:
                self.html = self._get_html(url)
        self.pricing2yaml_specification = self._load_specification()
        result_cycle = self._fix_cycle()
        if result_cycle:
            self.is_valid = True

    def _load_prompts(self) -> Dict[str, str]:
        prompts = {}
        for prompt_file in self.prompts_dir.glob("*.md"):
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompts[prompt_file.stem] = f.read()
        return prompts

    def _load_specification(self) -> str:
        spec_path = Path("src/amint/prompts/pricing2YamlSpecification.md")
        with open(spec_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    def _fix_cycle(self):
        # The initial validation outside the loop is removed.
        # The loop now handles all stages consistently

        while not self.finish:
            if self.counter >= self.max_retries:
                logging.error("Exceeded maximum number of retries.")
                self.finish = True
                return False  # Exit if max retries reached

            # Step 1: Ensure YAML is locally parsable. AI might be called here if it's not.
            # This call updates self.file_path if a fix is made by _ensure_valid_local_yaml.
            current_json_content_after_local_check = self._ensure_valid_local_yaml()
            
            if current_json_content_after_local_check is None:
                # This implies that local YAML parsing failed, 
                # _ensure_valid_local_yaml called AI, but the AI's fix was also invalid,
                # or another error occurred during the local fix attempt.
                logging.error("Local YAML parsing and AI-assisted fix failed. Cannot proceed with validation.")
                # Raising ValueError as in the original logic for unrecoverable local file state.
                raise ValueError("Unable to fix local YAML parsing error automatically, even with AI assist for local parsing.")

            # Step 2: Validate with the external service.
            # self.validate() reads from self.file_path, which _ensure_valid_local_yaml might have updated.
            response = self.validate() 
            response_json = response.json()
            logging.info(f"Validation attempt {self.counter + 1}/{self.max_retries} - Status: {response.status_code}, valid: {response_json.get('result').get('valid')}")
            if response_json.get('result').get('valid') == False and response_json.get('result').get('error') == "Request failed with status code 500":
                logging.error("Validation failed with a 500 error. This might indicate a server-side issue. Retrying with 'minizinc' solver.")
                response = self.validate('minizinc')
                response_json = response.json()
                logging.info(f"Validation attempt {self.counter + 1}/{self.max_retries} - Status: {response.status_code}, valid: {response_json.get('result').get('valid')}")

            if response.status_code == 200 and response_json.get('result').get('valid') == True:
                self.finish = True
                logging.info("Validation successful. The YAML file is valid.")
                return True  # Exit if validation is successful
            
            # Step 3: If validation fails (either non-200 status or a non-SUCCESS messageType),
            # log the error and call AI to fix based on the validator's feedback.
            # current_json_content_after_local_check is the JSON string representation
            # of the file content that was just validated.
            logging.info(f"Validation failed with errors: {str(response_json.get('result').get('error'))}")
            self._handle_validator_error(response_json, current_json_content_after_local_check) 
            
            self.counter += 1

    def validate(self, solver='choco') -> requests.Response:
        with open(self.file_path, 'rb') as file_handle:
            logging.info(f"Validating file: {self.file_path}")
            first_response = requests.post(f"{self.validator_endpoint}/pricing/analysis", files={'pricingFile': file_handle}, data={'operation': 'validate', 'solver': solver})
            logging.info(f"Initial validation response status: {first_response.status_code}")
            try:
                logging.info(f"Initial validation response JSON: {first_response.json()}")
            except requests.exceptions.JSONDecodeError:
                logging.info("Initial validation response not JSON.")
            job_id = first_response.json().get('jobId')
            
            if first_response.status_code != 202 or not job_id:
                logging.error(f"Initial validation failed with status {first_response.status_code} and no job_id.")
                if error_message := first_response.json().get('error'):
                    logging.error(f"Error message from validation: {error_message}")
                    # Return a mock response-like object with the error details
                    class MockResponse:
                        def __init__(self, status_code, error_message):
                            self._status_code = status_code
                            self._error_message = error_message
                        def json(self):
                            return {
                                "status_code": self._status_code,
                                "result": {
                                    "valid": False,
                                    "error": self._error_message
                                }
                            }
                        @property
                        def status_code(self):
                            return self._status_code
                    return MockResponse(first_response.status_code, error_message)

            # Step 2: Poll for validation result
            logging.info(f"Polling for validation result with job_id: {job_id}")
            second_response = requests.get(f"{self.validator_endpoint}/pricing/analysis/{job_id}")
            logging.info(f"Validation response status: {second_response.status_code}")
            try:
                logging.info(f"Validation response JSON: {second_response.json()}")
                start_time = time.time()
                while second_response.json().get('status') == 'PENDING' or second_response.json().get('status') == 'RUNNING':
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 900:  # Timeout after 900 seconds
                        logging.error("Validation timed out after 900 seconds.")
                        raise TimeoutError("Validation timed out.")
                    logging.info("Validation is still pending, waiting for result...")
                    second_response = requests.get(f"{self.validator_endpoint}/pricing/analysis/{job_id}")
                    logging.info(f"Polling response status: {second_response.status_code} - {elapsed_time:.2f} seconds elapsed")
                    try:
                        logging.info(f"Polling response JSON: {second_response.json()}")
                    except requests.exceptions.JSONDecodeError:
                        logging.info("Polling response not JSON.")
            except requests.exceptions.JSONDecodeError:
                logging.info("Validation response not JSON.")
        return second_response

    # def _prettify_html_content(self, html_data: Dict[str, Any]) -> str:
    #     plans = html_data.get('plans', "No plans data found.")
    #     features = html_data.get('features', "No features data found.")
    #     add_ons = html_data.get('add_ons', "No add-ons data found.")
    #     return f"""
    #     <!-- Plans-related HTML elements -->
    #     <div id=\"plans\">
    #         {plans}
    #     </div>
    #     <!-- Features-related HTML elements -->
    #     <div id=\"features\">
    #         {features}
    #     </div>
    #     <!-- Add-ons-related HTML elements -->
    #     <div id=\"add_ons\">
    #         {add_ons}
    #     </div>
    #     """
    def _prettify_html_content(self, html_data: Dict[str, Any]) -> str:
        """Prettifies HTML content from the provided dictionary."""
        plans = html_data.get('plans_markdown', "No plans data found.")
        features = html_data.get('features_markdown', "No features data found.")
        add_ons = html_data.get('add_ons_markdown', "No add-ons data found.")

        # Assuming plans, features, and add_ons are already in HTML format
        return f"""
        # Plans-related HTML content
        {plans if plans else "No plans data found."}

        ---
        # Features-related HTML content
        {features if features else "No features data found."}
        
        
        ---
        # Add-ons-related HTML content
        {add_ons if add_ons else "No add-ons data found."}
        """

    def _get_html(self, url: str) -> Optional[str]: # Mark url as unused if not implemented
        # Placeholder for HTML extraction logic, can be integrated with WebDriver if needed
        # If url is truly unused for now, consider removing it or prefixing with _
        logging.info(f"HTML extraction from URL ({url}) is not yet implemented.")
        return None

    def _ensure_valid_local_yaml(self) -> Optional[str]:
        """Ensures the YAML file is locally parsable, attempting AI fix if not."""
        try:
            json_string = self.parse_file_as_json()
            logging.info("Local YAML is already valid.")
            return json_string
        except yaml.YAMLError as e: # Catch specific YAML parsing errors
            logging.warning(f"Local YAML parsing error: {e}. Attempting AI fix.")
            raw_content = self._read_file_content()
            prompt = self._build_prompt(
                prompt_type="general",
                error_overview="YAML reader encountered an error locally during parsing.",
                error_details=str(e),
                json_content=raw_content
            )
            fixed_json_suggestion = self.ai_client.make_full_request(
                prompt,
                endpoint=self.endpoint or "FixYaml",
                function="fix_yaml_local_parse_error",
                transformation_call_id=self.transformation_call_id,
                llm_call_ids=self.llm_call_ids,
                json_output=False
            )
            try:
                json.loads(fixed_json_suggestion) # Check if AI returned valid JSON
                self.parse_json_as_yaml(fixed_json_suggestion)
                logging.info("AI successfully fixed local YAML parsing error.")
                return fixed_json_suggestion
            except (json.JSONDecodeError, yaml.YAMLError) as fix_e: # More specific exceptions
                logging.error(f"AI fix for local YAML parsing failed: {fix_e}. Raw AI output: {fixed_json_suggestion}")
                return None
        except Exception as e: # Catch any other unexpected error during local parsing/reading
            logging.error(f"Unexpected error in _ensure_valid_local_yaml: {e}")
            return None


    def _build_error_prompt_for_ai(self, errors: list, json_content: str) -> tuple[str, str]:
        """Builds the prompt and parameters for the AI client based on the error type."""
        error_details_str = str(errors) if str(errors).strip() else NO_SPECIFIC_ERROR_DETAILS

        prompt = self._build_prompt(
            prompt_type="general",
            error_overview="Validation error detected by the Pricing2Yaml validator.",
            error_details=error_details_str,
            json_content=json_content
        )
        function_name = "fix_yaml_validation_error"
        
        return prompt, function_name

    def _handle_validator_error(self, response_json: dict, json_content: str) -> None:
        errors = response_json.get('result', {}).get('error', '')

        logging.info("Handling validator error.")

        prompt, function_name = self._build_error_prompt_for_ai(
            errors, json_content
        )
        
        fixed_json_suggestion = self.ai_client.make_full_request(
            prompt,
            endpoint=self.endpoint or "FixYaml",
            function=function_name,
            transformation_call_id=self.transformation_call_id,
            llm_call_ids=self.llm_call_ids,
            json_output=False
        )

        try:
            json.loads(fixed_json_suggestion)
            self.parse_json_as_yaml(fixed_json_suggestion)
            logging.info(f"AI attempt to fix {errors} applied. Raw AI output was written to file.")
        except (json.JSONDecodeError, yaml.YAMLError) as ai_fix_error: # More specific exceptions
            logging.error(f"AI's suggested fix for {errors} was invalid: {ai_fix_error}. AI Output: {fixed_json_suggestion}")

    def _build_prompt(self, prompt_type: str, **kwargs) -> str:
        html_context = f"Finally, here is the original markdown content obtained from the HTML webpage that was used to generate the Pricing2Yaml JSON. Please, remember, you may need to fix errors that present multiple possible solutions—ensure that your changes always align with the pricing displayed in the markdown:\n<webpage_content>\n{self.html}\n</webpage_context>" if self.html else ""
        html_resolution_hint = "You must resolve errors with multiple possible solution paths by choosing the one that best aligns with the pricing displayed in the Markdown." if self.html else ""
        base_kwargs = dict(pricing2yaml_specification=self.pricing2yaml_specification, html_context=html_context, html_resolution_hint=html_resolution_hint)
        kwargs.update(base_kwargs)
        prompt_template = self.prompts.get(prompt_type)
        if not prompt_template:
            raise ValueError(f"Prompt template '{prompt_type}' not found.")
        return prompt_template.format(**kwargs)

    def parse_file_as_json(self) -> str:
        """Reads the YAML file and returns its content as a JSON string."""
        with open(self.file_path, 'r', encoding='utf-8') as file_handle:
            yaml_content = yaml.safe_load(file_handle)
        return json.dumps(yaml_content, indent=4)

    def parse_json_as_yaml(self, json_content: str) -> None:
        """Parses a JSON string, converts to YAML, and writes to the file, handling 'Infinity'."""
        try:
            # First, load the JSON string to a Python object
            data_from_json = json.loads(json_content)
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON content provided to parse_json_as_yaml: {e}")
            logging.error(f"Problematic JSON content: {json_content[:500]}...") # Log snippet
            raise # Re-raise the error to be handled by the caller

        # Recursively replace "Infinity" string with float('inf')
        def replace_infinity(value):
            if isinstance(value, str) and (value == "Infinity" or value == ".inf"):
                return float("inf")
            elif isinstance(value, dict):
                return {k: replace_infinity(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_infinity(item) for item in value]
            return value
        
        yaml_ready_data = replace_infinity(data_from_json)
        
        with open(self.file_path, 'w', encoding='utf-8') as file_handle:
            yaml.dump(yaml_ready_data, file_handle, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def _read_file_content(self) -> str:
        """Reads and returns the raw content of the YAML file."""
        with open(self.file_path, 'r', encoding='utf-8') as file_handle:
            return file_handle.read()