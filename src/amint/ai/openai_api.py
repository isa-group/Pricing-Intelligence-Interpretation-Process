"""
OpenAI-compatible API client for A-MINT.
Supports OpenAI, Gemini (via OpenAI API), and other OpenAI-compatible providers.
"""
import os
import json
import time
import logging
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv
from .base import AIClient, AIConfig
from .api_key_manager import APIKeyManager
from dataclasses import dataclass, field
from ..utils.csv_logger import CSVLogger
import uuid
from datetime import datetime, timedelta
from time import sleep
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
LOGS_PROMPTS_DIR = "logs/prompts"

LLM_LOG_FIELDS = [
    "llm_call_id",
    "timestamp",
    "endpoint",
    "function",
    "model_name",
    "response_time",
    "input_tokens",
    "output_tokens",
    "transformation_call_id"
]
llm_logger = CSVLogger("logs/llm_logs.csv", LLM_LOG_FIELDS)

# Se eliminaron las clases ChatSession y ChatSessionManager que manejaban las sesiones de chat

class OpenAIAPI(AIClient):
    """
    OpenAI-compatible API client implementation with API key rotation.
    
    Features:
    - Automatic API key rotation when quota limits are reached
    """
    
    def __init__(self, config: AIConfig):
        """
        Initialize the OpenAI-compatible API client.
        
        Args:
            config: Configuration with API key(s), base URL, and other settings.
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Load API keys and base URL from environment variables
        env_api_keys = []
        base_url = config.base_url
        
        # Determine provider based on base URL or environment variables
        if base_url:
            # Gemini via OpenAI API
            gemini_api_keys_str = os.getenv("OPENAI_API_KEYS")
            if gemini_api_keys_str:
                env_api_keys = [key.strip() for key in gemini_api_keys_str.split(",") if key.strip()]
            else:
                single_key = os.getenv("OPENAI_API_KEY")
                if single_key:
                    env_api_keys = [single_key]
        
        # Use configuration keys if provided, otherwise use environment variables
        api_keys = config.api_keys or env_api_keys
        
        if not api_keys:
            raise ValueError("No API keys found. Provide them in config.api_keys, "
                           "set OPENAI_API_KEY/OPENAI_API_KEYS "
                           "environment variables, or create a .env file with the appropriate variables.")

        # Store base URL
        self.base_url = base_url
        
        # Initialize API key manager
        self.key_manager = APIKeyManager(api_keys, config.key_cooldown_minutes)
        
        # Set the current API key in config for parent class
        config.api_key = self.key_manager.get_current_key()
        config.base_url = base_url
        
        super().__init__(config)
    
    def _configure(self) -> None:
        """Configure the OpenAI API client."""
        api_key = self.config.api_key
        
        try:
            self.client = OpenAI(
                api_key=api_key,
                base_url=self.config.base_url
            )
            logger.info(f"Configured OpenAI client with base URL: {self.config.base_url}")
        except Exception as e_configure:
            logging.error(f"Error configuring OpenAI API with key: {e_configure}")
            raise ValueError(f"Failed to configure OpenAI client with the provided API key: {e_configure}")
    
    def _reconfigure_with_new_key(self, new_api_key: str) -> None:
        """Reconfigure the client with a new API key."""
        try:
            self.client = OpenAI(
                api_key=new_api_key,
                base_url=self.config.base_url
            )
            self.config.api_key = new_api_key
            logging.info(f"Successfully reconfigured with new API key: {new_api_key[:8]}...")
        except Exception as e_configure:
            logging.error(f"Error reconfiguring OpenAI API with new key: {e_configure}")
            raise ValueError(f"Failed to reconfigure OpenAI client with new API key: {e_configure}")
    
    def _make_request(
        self,
        prompt: str,
        generation_config: Optional[Dict[str, Any]] = None,
        *,
        endpoint: str = None,
        function: str = None,
        transformation_call_id: str = None,
        llm_call_ids: list = None,
        use_better_model: bool = False
    ) -> tuple[str, str]:
        """
        Make a request to the OpenAI-compatible API and log the call with automatic key rotation.
        """
        max_key_rotation_attempts = len(self.key_manager.key_statuses)

        attempt = 0
        other_error_attempt = 0
        while attempt < max_key_rotation_attempts:
            try:
                random_uuid = uuid.uuid4().hex
                if not os.path.exists(LOGS_PROMPTS_DIR):
                    os.makedirs(LOGS_PROMPTS_DIR)
                with open(os.path.join(LOGS_PROMPTS_DIR, random_uuid + ".md"), "w") as f:
                    f.write(prompt)
                logging.info(f"Prompt saved to {LOGS_PROMPTS_DIR}/{random_uuid}.md")
                return self._attempt_request_with_current_key(
                    prompt, generation_config,
                    endpoint, function, transformation_call_id, llm_call_ids, use_better_model=use_better_model
                )
            except Exception as api_error:
                not_to_be_raised, error_type = self._handle_api_error(api_error, attempt, max_key_rotation_attempts)
                if not not_to_be_raised:
                    raise
                    
                if error_type == "other_error":
                    other_error_attempt += 1
                    if other_error_attempt >= 12:
                        not_to_be_raised, error_type = self._handle_api_error(
                            api_error, attempt, max_key_rotation_attempts, is_quota_error=True
                        )
                        other_error_attempt = 0
                
                if error_type == "quota_error":
                    attempt += 1

        raise ValueError("Failed to complete request after trying all available API keys.")
    
    def _attempt_request_with_current_key(
        self,
        prompt: str,
        generation_config: Optional[Dict[str, Any]],
        endpoint: str,
        function: str,
        transformation_call_id: str,
        llm_call_ids: list,
        use_better_model: bool = False
    ) -> tuple[str, str]:
        """Attempt a single request with the current API key."""
        current_key = self.key_manager.get_available_key()
        if not current_key:
            raise ValueError("No available API keys. All keys are in cooldown due to quota limits.")
        
        # Reconfigure if we've switched keys
        if current_key != self.config.api_key:
            self._reconfigure_with_new_key(current_key)
        
        model = self.config.model
        model = model if not use_better_model else self.config.better_model
        
        # Prepare single message for request
        messages = [{"role": "user", "content": prompt}]
        logger.info("Making request with single message")
        
        # Prepare request parameters
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": generation_config.get("temperature", self.config.temperature) if generation_config else self.config.temperature,
            "reasoning_effort": "high",
            # "max_tokens": 65536
        }
        
        llm_call_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(**request_params)
            
            response_text = response.choices[0].message.content
            
            # Check for problematic finish reasons
            finish_reason = response.choices[0].finish_reason
            possible_temperatures = [0.7, 0.6, 0.8, 0.5, 0.9, 1.0, 0.0]
            finish_attempt = 0
            if self._is_finish_reason_error(finish_reason) or not response_text:
                while finish_attempt < len(possible_temperatures):
                    logging.warning(f"Finish reason '{finish_reason}' detected. Retrying request with temperature {possible_temperatures[finish_attempt]}...")
                    request_params = {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": possible_temperatures[finish_attempt],
                        "reasoning_effort": "high",
                        # "max_tokens": 65536
                    }
                    sleep(10)  # Wait before retrying
                    response = self.client.chat.completions.create(**request_params)
                    finish_reason = response.choices[0].finish_reason
                    response_text = response.choices[0].message.content
                    if not self._is_finish_reason_error(finish_reason) and response_text:
                        logging.info(f"Successfully retried with temperature {possible_temperatures[finish_attempt]}")
                        break
                    finish_attempt += 1
            
            # Handle case where response content is None
            if response_text is None:
                logging.info(response)
                raise ValueError("Received None response from API. Please check the prompt and try again.")
            
            # Success - log and return
            self._log_successful_request(
                llm_call_id, start_time, endpoint, function, 
                transformation_call_id, response, llm_call_ids, model
            )
            
            return response_text, finish_reason
            
        except Exception:
            if llm_call_ids is not None:
                llm_call_ids.append(llm_call_id)
            raise
    
    def _log_successful_request(
        self,
        llm_call_id: str,
        start_time: float,
        endpoint: str,
        function: str,
        transformation_call_id: str,
        response: Any,
        llm_call_ids: list,
        model: str
    ) -> None:
        """Log a successful API request."""
        end_time = time.time()
        input_tokens = response.usage.prompt_tokens if hasattr(response, 'usage') and response.usage else None
        output_tokens = response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else None
        
        llm_logger.log({
            "llm_call_id": llm_call_id,
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint or "unknown",
            "function": function or "unknown",
            "model_name": model,
            "response_time": round(end_time - start_time, 3),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "transformation_call_id": transformation_call_id or "unknown"
        })
        
        if llm_call_ids is not None:
            llm_call_ids.append(llm_call_id)
    
    def _handle_api_error(
        self, 
        api_error: Exception, 
        attempt: int, 
        max_attempts: int, 
        is_quota_error: bool = False
    ) -> tuple[bool, str]:
        """
        Handle API errors and determine if retry should be attempted.
        
        Returns:
            True if retry should be attempted, False if error should be propagated
        """
        # Check if this is a quota-related error
        if self.key_manager.is_quota_error(api_error) or is_quota_error:
            current_key = self.config.api_key
            logger.warning(f"Quota error detected with key {current_key[:8]}...: {api_error}")
            
            # Mark current key as having quota error
            has_alternative = self.key_manager.mark_key_quota_error(current_key)
            
            if not has_alternative:
                logger.error("All API keys have reached their quota limits.")
                raise ValueError("All API keys have reached their quota limits. Please wait or add more keys.") from api_error
            
            # Continue to next iteration to try with a different key
            logger.info(f"Attempting retry with different API key (attempt {attempt + 1}/{max_attempts})")
            
            return (True, 'quota_error')
        elif self.key_manager.is_other_error(api_error):
            # Non-quota error - log and retry with delay
            logger.error(f"Non-quota error occurred: {api_error}")
            
            # Wait before retrying to avoid immediate re-requests
            logger.info("Waiting for 10 seconds before retrying...")
            sleep(10)

            return (True, 'other_error')
        else:
            # Non-quota error - propagate immediately
            return (False, 'other_error')
    
    def make_full_request(
        self,
        initial_prompt: str,
        max_tries: int = 5,
        *,
        endpoint: str = None,
        function: str = None,
        transformation_call_id: str = None,
        llm_call_ids: list = None,
        json_output: bool = True,
        use_better_model: bool = False
    ) -> str:
        """
        Make a complete request, handling truncation and logging all LLM calls.
        """
        accumulated_text = ""
        for attempt in range(1, max_tries + 1):
            # 1) get the next chunk
            prompt = initial_prompt if attempt == 1 else self._build_continue_prompt(initial_prompt, accumulated_text)
            response, finish_reason = self._make_request(
                prompt,
                endpoint=endpoint, function=function,
                transformation_call_id=transformation_call_id,
                llm_call_ids=llm_call_ids, use_better_model=use_better_model
            )
            parsed = self._parse_response(response)

            # 2) append and sanitize
            # accumulated_text = self._process_response_chunk(parsed, accumulated_text)
            # accumulated_text = self._sanitize_json(accumulated_text)
            
            accumulated_text += parsed
            
            # Check if the response was truncated due to reaching max tokens
            if finish_reason == "length":
                logger.warning(f"Response truncated at attempt {attempt}/{max_tries}. Accumulated text so far:\n{accumulated_text}")
                if attempt < max_tries:
                    continue
            
            if not json_output:
                if finish_reason != "length":
                    return parsed
                if not use_better_model:
                    logger.warning(f"Retrying with a more advanced model ({self.config.better_model}) due to problem")
                    return self.make_full_request(
                        initial_prompt, max_tries,
                        endpoint=endpoint, function=function,
                        transformation_call_id=transformation_call_id,
                        llm_call_ids=llm_call_ids, json_output=json_output, use_better_model=True
                    )
                if attempt == max_tries:
                    logger.error(f"Failed to generate valid response after {max_tries} attempts. Final accumulated text:\n{accumulated_text}")
                    raise ValueError(f"Could not form valid response after {max_tries} attempts.")
                

            # 3) try loading
            try:
                return json.dumps(json.loads(accumulated_text))
            except json.JSONDecodeError as e:
                logger.warning(f"Attempt {attempt}/{max_tries} JSON parse failed, accumulated text:\n{accumulated_text}")
                if not use_better_model:
                    logger.warning(f"Retrying with a more advanced model ({self.config.better_model}) due to JSON parse error: {e}")
                    return self.make_full_request(
                        initial_prompt, max_tries,
                        endpoint=endpoint, function=function,
                        transformation_call_id=transformation_call_id,
                        llm_call_ids=llm_call_ids, json_output=json_output, use_better_model=True
                    )
                if attempt == max_tries:
                    raise ValueError(f"Could not form valid JSON after {max_tries} attempts: {e}")

    def _build_continue_prompt(self, initial_prompt: str, accumulated_text: str) -> str:
        """Build a more robust prompt to continue generating JSON."""
        return f"""
        The initial request was to generate a response based on the following prompt:
        <initial_prompt>
        {initial_prompt}
        </initial_prompt>

        The generation was cut off. Here is the incomplete response that was generated:
        <incomplete_response>
        {accumulated_text} 
        </incomplete_response>
        
        Your task is to continue generating the response from where it was cut off. Do not repeat any previous content or add extra characters. Start immediately with the next expected token.
    # """
    
    def _process_response_chunk(self, response: str, accumulated_text: str) -> str:
        """Process a response chunk, handling boundaries."""
        if not accumulated_text:
            return response
        
        # Find the last complete JSON object or array
        last_complete = self._find_last_complete_json(accumulated_text)
        if last_complete:
            return last_complete + response
        return accumulated_text + response
    
    def _find_last_complete_json(self, text: str) -> Optional[str]:
        """Find the last complete JSON object or array in the text."""
        # Walk backwards and balance braces/brackets
        open_to_close = {"{":"}", "[":"]"}
        stack = []
        cut = None
        for i, ch in enumerate(text):
            if ch in open_to_close:
                stack.append(open_to_close[ch])
            elif stack and ch == stack[-1]:
                stack.pop()
                if not stack:
                    cut = i+1
        return text[:cut] if cut else None

    def _sanitize_json(self, text: str) -> str:
        """
        1) Strip out any stray control characters (0x00–0x1F, except \n, \r, \t),
        2) Then remove any trailing commas before a closing } or ].
        """
        # 1) drop invalid control chars
        #    allow: tab (09), linefeed (0A), carriage return (0D); drop others in 00–1F
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]+', '', text)
        # 2) strip dangling commas like ",}" or ",]"
        text = re.sub(r',\s*([}\]])', r'\1', text)
        return text

    def _parse_response(self, response: str) -> str:
        """Parse the response, handling code blocks."""
        # Remove markdown code block markers if present
        if response.startswith("```json"):
            response = response.split("```json")[1]
        elif response.startswith("```yaml"):
            response = response.split("```yaml")[1]
        elif response.startswith("```"):
            response = response.split("```")[1]
            
        # Remove any trailing code block markers
        if response.endswith("```"):
            response = response[:-3]
        
        return response.strip()

    def _is_finish_reason_error(self, finish_reason: str) -> bool:
        """
        Checks if the finish reason from the LLM indicates a potential error or incomplete response.

        Args:
            finish_reason: The finish_reason string from the API response.

        Returns:
            True if the finish reason is considered an error, False otherwise.
        """
        # 'STOP' is the desired outcome.
        # We consider 'MAX_LENGTH' and other reasons as errors to be retried.
        error_reasons = ["safety", "recitation", "other"]
        return finish_reason in error_reasons
