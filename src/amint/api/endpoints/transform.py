from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List
import asyncio
import logging
import uuid
import os
from pathlib import Path
import yaml
from ...extractors.web_driver import WebDriver
from ...transformers.yaml_serializer import YAMLSerializer
from ...extractors.extract_data import ExtractData, ExtractionConfig
from ...ai.base import AIConfig, AIClient
from ...ai.openai_api import OpenAIAPI
from fastapi.responses import FileResponse
from ...utils.csv_logger import CSVLogger
from datetime import datetime
from .task_manager import TaskManager
from ...validators.fix_yaml import FixYaml
from ...validators.validate_alignment import ValidateAlignment
import re
from urllib.parse import urlparse

router = APIRouter()
logger = logging.getLogger(__name__)

TRANSFORM_ENDPOINT = "/api/v1/transform"
FIX_ENDPOINT = "/api/v1/fix"

TRANSFORM_LOG_FIELDS = [
    "transformation_call_id",
    "timestamp",
    "response_time",
    "raw_html_length",
    "cleaned_html_length",
    "llm_call_ids",
]
transform_logger = CSVLogger("logs/transformation_logs.csv", TRANSFORM_LOG_FIELDS)

task_manager = TaskManager()

class TransformRequest(BaseModel):
    url: HttpUrl
    model: Optional[str] = "gemini-2.5-flash"
    max_tries: Optional[int] = 50  # New parameter for FixYaml
    base_url: Optional[str] = "https://generativelanguage.googleapis.com/v1beta/openai/"  # Custom endpoint URL for OpenAI-compatible APIs
    temperature: Optional[float] = 0.7  # Default temperature for model responses
    better_model: Optional[str] = "gemini-2.5-pro"  # Model for better quality responses

class TransformResponse(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None

class TransformResult(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TaskStatusResponse(BaseModel):
    status: str
    message: Optional[str] = None
    result_file: Optional[str] = None
    error: Optional[str] = None

class FixRequest(BaseModel):
    file_path: str
    url: Optional[str] = None
    max_tries: Optional[int] = 30
    use_html_context: Optional[bool] = True

# --- Background task functions ---
def background_transform(task_id: str, request: TransformRequest):
    async def _inner():
        transformation_call_id = str(uuid.uuid4())
        llm_call_ids = []
        start_time = datetime.now()
        raw_html_length = 0
        cleaned_html_length = 0
        try:
            with WebDriver() as driver:
                html_content = driver.get_page_content(str(request.url))
                raw_html_length = driver.raw_html_length
                cleaned_html_length = driver.cleaned_html_length
                if not html_content:
                    raise ValueError("Failed to fetch HTML content")

            ai_config = AIConfig(
                model=request.model,
                temperature=request.temperature,
                base_url=request.base_url,
                better_model=request.better_model
            )
            ai_client = OpenAIAPI(ai_config)
            extractor_config = ExtractionConfig(
                use_html_context=True,
                ai_client=ai_client
            )
            
            url_str = str(request.url)
            saas_name = _extract_saas_name(url_str)
            
            extractor = ExtractData(
                html=html_content,
                saas_name=saas_name,
                config=extractor_config
            )
            pricing_data = extractor.extract(
                transformation_call_id=transformation_call_id,
                llm_call_ids=llm_call_ids,
                endpoint=TRANSFORM_ENDPOINT
            )
            logging.info(f"Extracted pricing data: {pricing_data}")
            logging.info(f"Serializing data to YAML for {saas_name} at {url_str}")
            serializer = YAMLSerializer(saas_name=saas_name, url=url_str)
            yaml_data = serializer.from_json(
                plans=pricing_data.plans,
                features=pricing_data.features,
                add_ons=pricing_data.add_ons
            )
            logging.info(f"Serialized YAML data: {yaml_data}")
            yaml_content = serializer.serialize(yaml_data)
            logging.info(f"YAML content: {yaml_content}")
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{uuid.uuid4()}.yaml"
            with open(output_file, "w") as f:
                f.write(yaml_content)
                
            html_data = extractor.html_markdown
            
            max_iterations = request.max_tries
            current_iteration = 0
            is_valid = False
            is_aligned = True
            
            # Bucle para ejecutar FixYaml y ValidateAlignment hasta que ambos validen o se alcance el límite
            while (not is_valid or not is_aligned) and current_iteration < max_iterations:
                logging.info(f"Starting validation iteration {current_iteration + 1} of {max_iterations}")
                
                # Ejecutar FixYaml para corregir problemas en el archivo YAML
                fix_result = FixYaml(
                    file_path=str(output_file),
                    url=str(request.url),
                    max_retries=1,  # Solo hacemos 1 intento por iteración
                    use_html_context=True,
                    html_data=html_data,
                    ai_client=ai_client,
                    transformation_call_id=transformation_call_id,
                    endpoint=TRANSFORM_ENDPOINT,
                    llm_call_ids=llm_call_ids
                )
                
                is_valid = fix_result.is_valid
                logging.info(f"YAML validation status: {'Valid' if is_valid else 'Invalid'}")
                
                # if is_valid:
                #     validate_alignment = ValidateAlignment(
                #         pricing2yaml_file_path=str(output_file),
                #         scraped_markdown=html_data,
                #         ai_client=ai_client,
                #         transformation_call_id=transformation_call_id,
                #         endpoint=TRANSFORM_ENDPOINT,
                #         llm_call_ids=llm_call_ids
                #     )
                    
                #     alignment_result = validate_alignment.validate()
                #     is_aligned = alignment_result.get("status") == "aligned"
                #     logging.info(f"Alignment status: {alignment_result.get('status')}")

                #     if alignment_result.get("status") == "patched" and "updated_pricing2yaml" in alignment_result:
                #         with open(output_file, "w") as f:
                #             yaml.dump(alignment_result["updated_pricing2yaml"], f, sort_keys=False)
                #         logging.info("Applied alignment patches to YAML file")

                current_iteration += 1
                logging.info(f"Completed iteration {current_iteration}. Valid: {is_valid}, Aligned: {is_aligned}")
            
            final_status = "valid_and_aligned" if is_valid and is_aligned else "incomplete_validation"
            logging.info(f"Validation completed with status: {final_status} after {current_iteration} iterations")
            
            if not is_valid or not is_aligned:
                task_manager.set_error(task_id, "YAML validation failed after maximum iterations")
                raise ValueError("YAML validation failed after maximum iterations")
            
            end_time = datetime.now()
            transform_logger.log({
                "transformation_call_id": transformation_call_id,
                "timestamp": start_time.isoformat(),
                "response_time": (end_time - start_time).total_seconds(),
                "raw_html_length": raw_html_length,
                "cleaned_html_length": cleaned_html_length,
                "llm_call_ids": ",".join(llm_call_ids),
            })
            await task_manager.set_result(task_id, str(output_file))
        except Exception as e:
            await task_manager.set_error(task_id, str(e))
    asyncio.run(_inner())

def _validate_and_align_yaml(
    output_file: Path, 
    url: str, 
    html_data: str, 
    ai_client: AIClient, 
    transformation_call_id: str, 
    max_iterations: int, 
    llm_call_ids: list
) -> dict:
    """
    Ejecuta un bucle de validación y alineación para el archivo YAML generado.
    
    Args:
        output_file: Ruta del archivo YAML a validar
        url: URL de la página web
        html_data: Contenido HTML en formato markdown
        ai_client: Cliente de IA para las llamadas LLM
        transformation_call_id: ID de la llamada de transformación
        max_iterations: Número máximo de iteraciones
        llm_call_ids: Lista de IDs de llamadas LLM
        
    Returns:
        Diccionario con el estado final de la validación
    """
    current_iteration = 0
    is_valid = False
    is_aligned = True
    
    while (not is_valid or not is_aligned) and current_iteration < max_iterations:
        logging.info(f"Starting validation iteration {current_iteration + 1} of {max_iterations}")
        
        fix_result = FixYaml(
            file_path=str(output_file),
            url=url,
            max_retries=1,  # Now we only do 1 retry per iteration
            use_html_context=True,
            html_data=html_data,
            ai_client=ai_client,
            transformation_call_id=transformation_call_id,
            endpoint=TRANSFORM_ENDPOINT,
            llm_call_ids=llm_call_ids
        )
        
        is_valid = fix_result.is_valid
        logging.info(f"YAML validation status: {'Valid' if is_valid else 'Invalid'}")
        
        # if is_valid:
        #     validate_alignment = ValidateAlignment(
        #         pricing2yaml_file_path=str(output_file),
        #         scraped_markdown=html_data,
        #         ai_client=ai_client,
        #         transformation_call_id=transformation_call_id,
        #         endpoint=TRANSFORM_ENDPOINT,
        #         llm_call_ids=llm_call_ids
        #     )
            
        #     alignment_result = validate_alignment.validate()
        #     is_aligned = alignment_result.get("status") == "aligned"
        #     logging.info(f"Alignment status: {alignment_result.get('status')}")
            
        #     if alignment_result.get("status") == "patched" and "updated_pricing2yaml" in alignment_result:
        #         with open(output_file, "w") as f:
        #             yaml.dump(alignment_result["updated_pricing2yaml"], f, sort_keys=False)
        #         logging.info("Applied alignment patches to YAML file")
        
        current_iteration += 1
        logging.info(f"Completed iteration {current_iteration}. Valid: {is_valid}, Aligned: {is_aligned}")

    # Determine final status
    final_status = "valid_and_aligned" if is_valid and is_aligned else "incomplete_validation"
    logging.info(f"Validation completed with status: {final_status} after {current_iteration} iterations")
    
    return {
        "is_valid": is_valid,
        "is_aligned": is_aligned,
        "iterations": current_iteration,
        "status": final_status
    }

def background_transform(task_id: str, request: TransformRequest):
    async def _inner():
        transformation_call_id = str(uuid.uuid4())
        llm_call_ids = []
        start_time = datetime.now()
        raw_html_length = 0
        cleaned_html_length = 0
        try:
            with WebDriver() as driver:
                html_content = driver.get_page_content(str(request.url))
                raw_html_length = driver.raw_html_length
                cleaned_html_length = driver.cleaned_html_length
                if not html_content:
                    task_manager.set_error(task_id, "Failed to fetch HTML content")
                    raise ValueError("Failed to fetch HTML content")

            ai_config = AIConfig(
                model=request.model,
                temperature=request.temperature,
                base_url=request.base_url,
                better_model=request.better_model
            )
            ai_client = OpenAIAPI(ai_config)
            extractor_config = ExtractionConfig(
                use_html_context=True,
                ai_client=ai_client
            )
            
            url_str = str(request.url)
            saas_name = _extract_saas_name(url_str)
            
            extractor = ExtractData(
                html=html_content,
                saas_name=saas_name,
                config=extractor_config
            )
            pricing_data = extractor.extract(
                transformation_call_id=transformation_call_id,
                llm_call_ids=llm_call_ids,
                endpoint=TRANSFORM_ENDPOINT
            )
            logging.info(f"Extracted pricing data: {pricing_data}")
            logging.info(f"Serializing data to YAML for {saas_name} at {url_str}")
            serializer = YAMLSerializer(saas_name=saas_name, url=url_str)
            yaml_data = serializer.from_json(
                plans=pricing_data.plans,
                features=pricing_data.features,
                add_ons=pricing_data.add_ons
            )
            logging.info(f"Serialized YAML data: {yaml_data}")
            yaml_content = serializer.serialize(yaml_data)
            logging.info(f"YAML content: {yaml_content}")
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{uuid.uuid4()}.yaml"
            with open(output_file, "w") as f:
                f.write(yaml_content)
                
            html_data = extractor.html_markdown
            
            # Ejecutar el bucle de validación y alineación
            validation_result = _validate_and_align_yaml(
                output_file=output_file,
                url=url_str,
                html_data=html_data,
                ai_client=ai_client,
                transformation_call_id=transformation_call_id,
                max_iterations=request.max_tries,
                llm_call_ids=llm_call_ids
            )
            
            logging.info(f"Validation completed with status: {validation_result['status']}")
            
            if not validation_result["is_valid"] or not validation_result["is_aligned"]:
                task_manager.set_error(task_id, "YAML validation failed after maximum iterations")
                raise ValueError("YAML validation failed after maximum iterations")
            
            end_time = datetime.now()
            transform_logger.log({
                "transformation_call_id": transformation_call_id,
                "timestamp": start_time.isoformat(),
                "response_time": (end_time - start_time).total_seconds(),
                "raw_html_length": raw_html_length,
                "cleaned_html_length": cleaned_html_length,
                "llm_call_ids": ",".join(llm_call_ids)
            })
            await task_manager.set_result(task_id, str(output_file))
        except Exception as e:
            await task_manager.set_error(task_id, str(e))
    asyncio.run(_inner())

def background_fix(task_id: str, file_path: str, url: Optional[str], max_tries: int, use_html_context: bool):
    async def _inner():
        try:
            ai_config = AIConfig(
                model="gemini-2.5-flash",
                temperature=0.0,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                better_model="gemini-2.5-pro"
            )
            ai_client = OpenAIAPI(ai_config)
            FixYaml(
                file_path=file_path,
                url=url,
                max_retries=max_tries,
                use_html_context=use_html_context,
                ai_client=ai_client,
                transformation_call_id=str(uuid.uuid4()),
                endpoint=FIX_ENDPOINT,
                llm_call_ids=[]
            )
            # Assume FixYaml modifies the file in place
            await task_manager.set_result(task_id, file_path)
        except Exception as e:
            await task_manager.set_error(task_id, str(e))
    asyncio.run(_inner())
    
def _extract_saas_name(raw_url: str) -> str:
    """
    Finds the last http(s)://… segment in raw_url,
    parses its hostname, strips 'www.' and returns the first label.
    """
    # 1) Grab all occurrences of "http(s)://<host>" up to the next slash
    urls = re.findall(r"(https?://[^/]+)", raw_url)
    # 2) If we found at least one, use the last one; otherwise fall back to raw_url
    target = urls[-1] if urls else raw_url
    # 3) Parse its hostname
    host = urlparse(target).hostname or ""
    # 4) Strip any 'www.' prefix
    if host.startswith("www."):
        host = host[4:]
    # 5) Return the first label
    return host.split(".")[0] if host else ""


# --- Endpoints ---

@router.post("/transform", response_model=TransformResponse)
async def transform_url(request: TransformRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await task_manager.create_task(task_id)
    background_tasks.add_task(background_transform, task_id, request)
    return TransformResponse(task_id=task_id, status="pending", message="Transformation started")

@router.get("/transform/status/{task_id}", response_model=TaskStatusResponse)
async def get_transform_status(task_id: str):
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] == "completed":
        return FileResponse(
            task["result"],
            media_type="application/x-yaml",
            filename=f"pricing_{Path(task["result"]).stem}.yaml"
        )
    return TaskStatusResponse(status=task["status"], error=task["error"])

@router.post("/fix", response_model=TransformResponse)
async def fix_yaml_endpoint(request: FixRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    await task_manager.create_task(task_id)
    background_tasks.add_task(background_fix, task_id, request.file_path, request.url, request.max_tries, request.use_html_context)
    return TransformResponse(task_id=task_id, status="pending", message="Fixing started")

@router.get("/fix/status/{task_id}", response_model=TaskStatusResponse)
async def get_fix_status(task_id: str):
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] == "completed":
        return FileResponse(
            task["result"],
            media_type="application/x-yaml",
            filename=f"fixed_{Path(task["result"]).stem}.yaml"
        )
    return TaskStatusResponse(status=task["status"], error=task["error"])