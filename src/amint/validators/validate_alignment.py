from pathlib import Path
from typing import Optional, Dict, Any, Union, List
import json
import yaml
import logging
import re
from ..ai.base import AIClient

logger = logging.getLogger(__name__)

class ValidateAlignment:
    """
    Validates alignment between a Pricing2YAML file and scraped markdown content.
    Generates ideal markdown from the YAML file and compares it with scraped content.
    If misaligned, attempts to patch the YAML file to match the scraped content.
    """
    
    def __init__(
        self,
        pricing2yaml_file_path: str,
        scraped_markdown: str,
        ai_client: AIClient,
        prompts_dir: str = "src/amint/prompts/validate_alignment",
        transformation_call_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        llm_call_ids: Optional[list] = None
    ):
        """
        Initialize the ValidateAlignment utility.
        
        Args:
            pricing2yaml_file_path: Path to the Pricing2YAML file to validate
            scraped_markdown: Markdown content scraped from the live SaaS pricing page
            ai_client: AI client for LLM interactions
            prompts_dir: Directory containing prompt templates
            transformation_call_id: Optional transformation call ID for tracking
            endpoint: Optional endpoint for the AI client
            llm_call_ids: Optional list of LLM call IDs for tracking
        """
        self.pricing2yaml_file_path = pricing2yaml_file_path
        self.scraped_markdown = scraped_markdown
        self.ai_client = ai_client
        self.prompts_dir = Path(prompts_dir)
        self.transformation_call_id = transformation_call_id
        self.endpoint = endpoint
        self.llm_call_ids = llm_call_ids if llm_call_ids is not None else []
        
        # Load prompts and specification
        self.prompts = self._load_prompts()
        self.pricing2yaml_specification = self._load_specification()
        
        # Load the pricing2yaml content
        self.pricing2yaml_content = self._load_pricing2yaml_file()
        
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompt templates from the prompts directory."""
        prompts = {}
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            return prompts
            
        for prompt_file in self.prompts_dir.glob("*.md"):
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompts[prompt_file.stem] = f.read()
        return prompts
    
    def _load_specification(self) -> str:
        """Load the Pricing2YAML specification."""
        spec_path = Path("src/amint/prompts/pricing2YamlSpecification.md")
        if not spec_path.exists():
            logger.warning(f"Specification file not found: {spec_path}")
            return ""
            
        with open(spec_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    
    def _load_pricing2yaml_file(self) -> Dict[str, Any]:
        """Load and parse the Pricing2YAML file."""
        try:
            with open(self.pricing2yaml_file_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Failed to load Pricing2YAML file {self.pricing2yaml_file_path}: {e}")
            raise ValueError(f"Cannot load Pricing2YAML file: {e}")
    
    def validate(self) -> bool:
        """
        Validate the alignment of the Pricing2YAML file with the scraped markdown.
        
        This method orchestrates the entire validation process:
        1. Generates Pricing2YAML file aligned with scraped markdown.
        2. Returns True if aligned, False if patched.
        """
        try:
            logger.info("Starting alignment validation...")
            prompt = self.prompts.get("validate_alignment")
            if not prompt:
                logger.error("Prompt for validate_alignment not found.")
                return False
            prompt = prompt.format(
                pricing2yaml_specification=self.pricing2yaml_specification,
                pricing2yaml_content=json.dumps(self.pricing2yaml_content, indent=2),
                scraped_markdown=self.scraped_markdown
            )
            response = self.ai_client.make_full_request(
                prompt,
                endpoint=self.endpoint or "ValidateAlignment",
                function="validate_alignment",
                transformation_call_id=self.transformation_call_id,
                llm_call_ids=self.llm_call_ids,
                json_output=True
            )
            return response
        except Exception as e:
            logger.error(f"Error during alignment validation: {e}")
            raise ValueError(f"Alignment validation failed: {e}")

    def old_validate(self) -> Dict[str, Any]:
        """
        Main validation method that orchestrates the alignment process.
        
        Returns:
            Dictionary with status and results of the validation
        """
        try:
            # Step 1: Generate ideal markdown from the Pricing2YAML file
            ideal_markdown = self._generate_ideal_markdown()
            logging.info(ideal_markdown)
            logging.info("Generated ideal markdown from Pricing2YAML.")
            
            ideal_markdown = self._normalize_markdown_dashes(ideal_markdown)
            
            # Step 2: Compare ideal markdown with scraped markdown
            comparison = self._compare_markdown_content(ideal_markdown, self.scraped_markdown)
            
            logging.info("Comparison result: " + json.dumps(comparison, indent=2))
            
            is_aligned = comparison.get("aligned", False)

            confidence = comparison.get("confidence", 1.0)

            if (is_aligned and confidence >= 0.7) or (not is_aligned and confidence < 0.7):
                logger.info("Content is semantically aligned.")
                return {
                    "status": "aligned",
                    "markdown": ideal_markdown
                }
            
            differences = comparison.get("differences", [])
            
            # Step 3: If not aligned, attempt to patch the YAML file
            patched_result = self._patch_pricing2yaml_file(ideal_markdown, differences)

            logger.info("Patched Pricing2YAML file with updated content.")

            return {
                "status": "patched",
                "updated_pricing2yaml": patched_result["updated_yaml"]
            }
            
        except Exception as e:
            logger.error(f"Error during alignment validation: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _generate_ideal_markdown(self) -> str:
        """
        Generate ideal markdown from the Pricing2YAML content.
        
        Returns:
            Generated markdown content
        """
        prompt_template = self.prompts.get("generate_ideal_markdown")
        
        prompt = prompt_template.format(
            pricing2yaml_specification=self.pricing2yaml_specification,
            pricing2yaml_content=json.dumps(self.pricing2yaml_content, indent=2)
        )
        
        response = self.ai_client.make_full_request(
            prompt,
            endpoint=self.endpoint or "ValidateAlignment",
            function="generate_ideal_markdown",
            transformation_call_id=self.transformation_call_id,
            llm_call_ids=self.llm_call_ids,
            json_output=False
        )
        
        # Remove markdown code blocks if present
        if response.startswith('```'):
            response = response.split('```')[1]
            
        if response.endswith('```'):
            response = response[:-3]
            
        
        return response.strip()
    
    def _compare_markdown_content(self, ideal_markdown: str, scraped_markdown: str) -> bool:
        """
        Compare ideal markdown with scraped markdown to determine alignment.
        
        Args:
            ideal_markdown: Generated markdown from Pricing2YAML
            scraped_markdown: Markdown scraped from the live page
            
        Returns:
            True if content is semantically aligned, False otherwise
        """
        prompt_template = self.prompts.get("compare_markdown")
        if not prompt_template:
            # Fallback prompt if template not found
            prompt_template = self._get_fallback_compare_markdown_prompt()
        
        prompt = prompt_template.format(
            ideal_markdown=ideal_markdown,
            scraped_markdown=scraped_markdown
        )
        
        response = self.ai_client.make_full_request(
            prompt,
            endpoint=self.endpoint or "ValidateAlignment",
            function="compare_markdown_content",
            transformation_call_id=self.transformation_call_id,
            llm_call_ids=self.llm_call_ids,
            json_output=True
        )
        
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse comparison result: {response}")
            return False

    def _patch_pricing2yaml_file(self, ideal_markdown: str, differences: List[str]) -> Dict[str, str]:
        """
        Patch the Pricing2YAML file to align with scraped markdown.
        
        Args:
            ideal_markdown: The generated markdown that doesn't match scraped content
            
        Returns:
            Dictionary with updated YAML and regenerated markdown
        """
        prompt_template = self.prompts.get("patch_pricing2yaml")
        
        prompt = prompt_template.format(
            pricing2yaml_specification=self.pricing2yaml_specification,
            current_pricing2yaml=json.dumps(self.pricing2yaml_content, indent=2),
            ideal_markdown=ideal_markdown,
            scraped_markdown=self.scraped_markdown,
            differences=json.dumps(differences, indent=2) if differences else "There are no differences provided. Please look at the generated markdown and scraped (original) markdown, compare the following two markdown contents and determine if they are semantically equivalent in terms of pricing information. This task is similar to a metamorphic test, where you need to ensure that the content aligns in meaning, even if the formatting or presentation differs."
        )
        
        response = self.ai_client.make_full_request(
            prompt,
            endpoint=self.endpoint or "ValidateAlignment",
            function="patch_pricing2yaml_file",
            transformation_call_id=self.transformation_call_id,
            llm_call_ids=self.llm_call_ids,
            json_output=True
        )
        
        logger.info(f"Patch response: {response}")
        
        try:
            result = json.loads(response)
            updated_yaml_content = result.get("updated_pricing2yaml")
            
            # Save the updated YAML file
            if updated_yaml_content:
                self._save_updated_yaml(updated_yaml_content)
                
                # # Regenerate markdown from updated YAML
                # regenerated_markdown = self._regenerate_markdown_from_yaml(updated_yaml_content)
                
                return {
                    "updated_yaml": updated_yaml_content,
                    # "regenerated_markdown": regenerated_markdown
                }
            else:
                raise ValueError("No updated YAML content in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse patch result: {e}")
            logger.error(f"Response: {response}")
            raise ValueError(f"Failed to patch Pricing2YAML file: {e}")
    
    def _save_updated_yaml(self, yaml_content: Union[str, Dict[str, Any]]) -> None:
        """Save the updated YAML content to file."""
        try:
            if isinstance(yaml_content, str):
                # If it's a string, try to parse it as JSON first, then convert to YAML
                if yaml_content.startswith('```yaml') and yaml_content.endswith('```'):
                    yaml_content = yaml_content.split('```yaml')[1].strip()
                    yaml_content = yaml_content[:-3].strip()
                elif yaml_content.startswith('```json') and yaml_content.endswith('```'):
                    yaml_content = yaml_content.split('```json')[1].strip()
                    yaml_content = yaml_content[:-3].strip()

                # Attempt to parse as JSON first
                try:
                    data = json.loads(yaml_content)
                except json.JSONDecodeError:
                    # If not JSON, assume it's already YAML string
                    data = yaml.safe_load(yaml_content)
            else:
                data = yaml_content
            
            with open(self.pricing2yaml_file_path, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False, sort_keys=False, allow_unicode=True)
                
        except Exception as e:
            logger.error(f"Failed to save updated YAML: {e}")
            raise ValueError(f"Cannot save updated YAML file: {e}")
    
    def _regenerate_markdown_from_yaml(self, updated_yaml_content: Union[str, Dict[str, Any]]) -> str:
        """Regenerate markdown from the updated YAML content."""
        if isinstance(updated_yaml_content, str):
            try:
                yaml_data = json.loads(updated_yaml_content)
            except json.JSONDecodeError:
                yaml_data = yaml.safe_load(updated_yaml_content)
        else:
            yaml_data = updated_yaml_content
        
        prompt_template = self.prompts.get("generate_ideal_markdown")
        
        prompt = prompt_template.format(
            pricing2yaml_specification=self.pricing2yaml_specification,
            pricing2yaml_content=json.dumps(yaml_data, indent=2)
        )
        
        response = self.ai_client.make_full_request(
            prompt,
            endpoint=self.endpoint or "ValidateAlignment",
            function="regenerate_markdown_from_updated_yaml",
            transformation_call_id=self.transformation_call_id,
            llm_call_ids=self.llm_call_ids,
            json_output=False
        )
        
        # Remove markdown code blocks if present
        if response.startswith('```'): 
            response = response.split('```')[1]
        if response.endswith('```'):
            response = response[:-3]
        
        return response.strip()
    
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