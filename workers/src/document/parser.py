"""Core document parsing logic using LLM for content extraction."""

import json
import base64
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from openai import OpenAI
from PIL import Image

from .preprocessing import ProcessedDocument, DocumentFormat
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llm.factory import LLMClientFactory, LLMProvider
from llm.exceptions import LLMProviderError

logger = structlog.get_logger(__name__)


class ExtractionMode(str, Enum):
    """Different modes for content extraction."""
    STRUCTURED = "structured"  # Extract structured data (JSON)
    SUMMARY = "summary"        # Generate summary
    FULL_TEXT = "full_text"    # Extract all text content
    CUSTOM = "custom"          # Custom extraction with user prompt


@dataclass
class TokenUsage:
    """Token usage information from LLM API."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float = 0.0


@dataclass
class ParsingResult:
    """Result of document parsing operation."""
    task_id: str
    extracted_content: Dict[str, Any]
    confidence_score: float
    processing_time: float
    token_usage: TokenUsage
    metadata: Dict[str, Any]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "extracted_content": self.extracted_content,
            "confidence_score": self.confidence_score,
            "processing_time": self.processing_time,
            "token_usage": {
                "prompt_tokens": self.token_usage.prompt_tokens,
                "completion_tokens": self.token_usage.completion_tokens,
                "total_tokens": self.token_usage.total_tokens,
                "estimated_cost": self.token_usage.estimated_cost
            },
            "metadata": self.metadata,
            "error_message": self.error_message
        }


class DocumentParser:
    """Core document parser using LLM for intelligent content extraction."""
    
    def __init__(
        self,
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        model_name: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.1
    ):
        """
        Initialize document parser.
        
        Args:
            llm_provider: LLM provider to use
            model_name: Specific model name (uses provider default if None)
            max_tokens: Maximum tokens for completion
            temperature: Temperature for LLM generation
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = None
        
        # Initialize LLM client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the LLM client."""
        try:
            self.client = LLMClientFactory.create_client(self.llm_provider)
            
            # Use model from client config if not specified
            if not self.model_name and hasattr(self.client, '_model'):
                self.model_name = self.client._model
            
            # Fallback to default model
            if not self.model_name:
                self.model_name = "gpt-4-vision-preview"
            
            logger.info(
                "LLM client initialized",
                provider=self.llm_provider.value,
                model=self.model_name
            )
            
        except Exception as e:
            logger.error("Failed to initialize LLM client", error=str(e))
            raise LLMProviderError(f"LLM client initialization failed: {str(e)}", self.llm_provider.value)
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 for vision models.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        try:
            with Image.open(image_path) as img:
                # Resize large images to reduce token usage
                max_size = (1024, 1024)
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save to bytes and encode
                import io
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=85)
                img_byte_arr = img_byte_arr.getvalue()
                
                return base64.b64encode(img_byte_arr).decode('utf-8')
                
        except Exception as e:
            logger.error("Failed to encode image", image_path=image_path, error=str(e))
            raise Exception(f"Image encoding failed: {str(e)}")
    
    def _build_system_prompt(self, extraction_mode: ExtractionMode, custom_prompt: Optional[str] = None) -> str:
        """
        Build system prompt based on extraction mode.
        
        Args:
            extraction_mode: Mode for content extraction
            custom_prompt: Custom prompt for CUSTOM mode
            
        Returns:
            System prompt string
        """
        base_prompt = """You are an expert document analysis AI. Your task is to analyze the provided document and extract information according to the specified mode.

Always respond with valid JSON format. Be thorough but concise in your analysis."""

        if extraction_mode == ExtractionMode.STRUCTURED:
            return base_prompt + """

EXTRACTION MODE: STRUCTURED
Extract structured information from the document and organize it into a JSON format with the following structure:
{
    "document_type": "type of document (e.g., invoice, contract, report, etc.)",
    "title": "document title or main heading",
    "summary": "brief summary of the document content",
    "key_information": {
        "dates": ["list of important dates found"],
        "names": ["list of person/organization names"],
        "amounts": ["list of monetary amounts or quantities"],
        "locations": ["list of addresses or locations"],
        "contact_info": ["list of phone numbers, emails, etc."]
    },
    "sections": [
        {
            "heading": "section heading",
            "content": "section content summary"
        }
    ],
    "tables": [
        {
            "title": "table title or description",
            "data": "structured representation of table data"
        }
    ],
    "metadata": {
        "language": "detected language",
        "confidence": "confidence score 0-1",
        "processing_notes": "any relevant processing notes"
    }
}"""

        elif extraction_mode == ExtractionMode.SUMMARY:
            return base_prompt + """

EXTRACTION MODE: SUMMARY
Provide a comprehensive summary of the document in JSON format:
{
    "executive_summary": "high-level overview of the document",
    "main_points": ["list of key points or findings"],
    "conclusions": ["list of conclusions or recommendations"],
    "action_items": ["list of action items if any"],
    "metadata": {
        "document_length": "estimated length category (short/medium/long)",
        "complexity": "complexity level (simple/moderate/complex)",
        "confidence": "confidence score 0-1"
    }
}"""

        elif extraction_mode == ExtractionMode.FULL_TEXT:
            return base_prompt + """

EXTRACTION MODE: FULL_TEXT
Extract and organize all text content from the document in JSON format:
{
    "full_text": "complete text content of the document",
    "text_structure": {
        "headings": ["list of all headings and subheadings"],
        "paragraphs": "number of paragraphs",
        "lists": ["extracted list items"],
        "tables": ["table content in text format"]
    },
    "formatting": {
        "has_images": "boolean indicating presence of images",
        "has_tables": "boolean indicating presence of tables",
        "has_headers_footers": "boolean indicating headers/footers"
    },
    "metadata": {
        "word_count": "estimated word count",
        "language": "detected language",
        "confidence": "confidence score 0-1"
    }
}"""

        elif extraction_mode == ExtractionMode.CUSTOM and custom_prompt:
            return base_prompt + f"""

EXTRACTION MODE: CUSTOM
{custom_prompt}

Ensure your response is in valid JSON format."""

        else:
            return base_prompt + """

EXTRACTION MODE: DEFAULT
Extract key information from the document in JSON format with appropriate structure based on the document type."""
    
    def _build_user_message(self, processed_doc: ProcessedDocument) -> List[Dict[str, Any]]:
        """
        Build user message for LLM API call.
        
        Args:
            processed_doc: Processed document with content
            
        Returns:
            List of message content parts
        """
        content_parts = []
        
        # Add text content if available
        if processed_doc.has_text_content():
            content_parts.append({
                "type": "text",
                "text": f"Document Text Content:\n\n{processed_doc.text_content}"
            })
        
        # Add images if available and model supports vision
        if processed_doc.has_images():
            try:
                for image_path in processed_doc.image_paths[:3]:  # Limit to 3 images
                    encoded_image = self._encode_image(image_path)
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}",
                            "detail": "high"
                        }
                    })
            except Exception as e:
                logger.warning("Failed to encode images for vision model", error=str(e))
        
        # Add document metadata
        if processed_doc.metadata:
            metadata_text = f"\n\nDocument Metadata:\n{json.dumps(processed_doc.metadata, indent=2)}"
            if content_parts and content_parts[0]["type"] == "text":
                content_parts[0]["text"] += metadata_text
            else:
                content_parts.append({
                    "type": "text",
                    "text": f"Document Metadata:\n{json.dumps(processed_doc.metadata, indent=2)}"
                })
        
        # Ensure we have at least some content
        if not content_parts:
            content_parts.append({
                "type": "text",
                "text": f"Document: {processed_doc.original_filename}\nFormat: {processed_doc.format.value}\nNo extractable content found."
            })
        
        return content_parts
    
    def _call_llm_api(
        self,
        system_prompt: str,
        user_content: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], TokenUsage]:
        """
        Make API call to LLM service.
        
        Args:
            system_prompt: System prompt for the model
            user_content: User message content parts
            
        Returns:
            Tuple of (response_content, token_usage)
            
        Raises:
            LLMProviderError: If API call fails
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            logger.info(
                "Making LLM API call",
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # Extract response content
            response_content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                parsed_content = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON response, returning raw content", error=str(e))
                parsed_content = {"raw_response": response_content, "parse_error": str(e)}
            
            # Extract token usage
            usage = response.usage
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens
            )
            
            logger.info(
                "LLM API call successful",
                prompt_tokens=token_usage.prompt_tokens,
                completion_tokens=token_usage.completion_tokens,
                total_tokens=token_usage.total_tokens
            )
            
            return parsed_content, token_usage
            
        except Exception as e:
            logger.error("LLM API call failed", error=str(e))
            raise LLMProviderError(f"LLM API call failed: {str(e)}", self.llm_provider.value)
    
    def _validate_and_post_process(
        self,
        extracted_content: Dict[str, Any],
        processed_doc: ProcessedDocument
    ) -> Tuple[Dict[str, Any], float]:
        """
        Validate and post-process extracted content.
        
        Args:
            extracted_content: Raw extracted content from LLM
            processed_doc: Original processed document
            
        Returns:
            Tuple of (validated_content, confidence_score)
        """
        confidence_score = 0.8  # Default confidence
        
        try:
            # Extract confidence from metadata if available
            if isinstance(extracted_content, dict):
                metadata = extracted_content.get('metadata', {})
                if 'confidence' in metadata:
                    try:
                        confidence_score = float(metadata['confidence'])
                    except (ValueError, TypeError):
                        pass
            
            # Validate required fields based on extraction type
            if isinstance(extracted_content, dict):
                # Ensure we have some meaningful content
                content_keys = [k for k in extracted_content.keys() if k != 'metadata']
                if not content_keys:
                    logger.warning("No meaningful content extracted")
                    confidence_score *= 0.5
                
                # Add document format information
                extracted_content['document_format'] = processed_doc.format.value
                extracted_content['original_filename'] = processed_doc.original_filename
                
                # Add processing metadata
                if 'metadata' not in extracted_content:
                    extracted_content['metadata'] = {}
                
                extracted_content['metadata'].update({
                    'processing_method': 'llm_extraction',
                    'model_used': self.model_name,
                    'provider': self.llm_provider.value,
                    'document_size': processed_doc.file_size,
                    'has_text_content': processed_doc.has_text_content(),
                    'has_images': processed_doc.has_images()
                })
            
            logger.info(
                "Content validation completed",
                confidence_score=confidence_score,
                content_keys=list(extracted_content.keys()) if isinstance(extracted_content, dict) else "non-dict"
            )
            
            return extracted_content, confidence_score
            
        except Exception as e:
            logger.error("Content validation failed", error=str(e))
            return extracted_content, 0.3  # Low confidence on validation failure
    
    def parse_document(
        self,
        processed_doc: ProcessedDocument,
        task_id: str,
        extraction_mode: ExtractionMode = ExtractionMode.STRUCTURED,
        custom_prompt: Optional[str] = None
    ) -> ParsingResult:
        """
        Parse document using LLM for intelligent content extraction.
        
        Args:
            processed_doc: Preprocessed document
            task_id: Task ID for tracking
            extraction_mode: Mode for content extraction
            custom_prompt: Custom prompt for CUSTOM mode
            
        Returns:
            ParsingResult with extracted content and metadata
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(
                "Starting document parsing",
                task_id=task_id,
                document_format=processed_doc.format.value,
                extraction_mode=extraction_mode.value,
                has_text=processed_doc.has_text_content(),
                has_images=processed_doc.has_images()
            )
            
            # Build prompts
            system_prompt = self._build_system_prompt(extraction_mode, custom_prompt)
            user_content = self._build_user_message(processed_doc)
            
            # Make LLM API call
            extracted_content, token_usage = self._call_llm_api(system_prompt, user_content)
            
            # Validate and post-process results
            validated_content, confidence_score = self._validate_and_post_process(
                extracted_content, processed_doc
            )
            
            processing_time = time.time() - start_time
            
            # Create parsing result
            result = ParsingResult(
                task_id=task_id,
                extracted_content=validated_content,
                confidence_score=confidence_score,
                processing_time=processing_time,
                token_usage=token_usage,
                metadata={
                    'extraction_mode': extraction_mode.value,
                    'model_name': self.model_name,
                    'provider': self.llm_provider.value,
                    'document_summary': processed_doc.get_content_summary(),
                    'processing_timestamp': time.time()
                }
            )
            
            logger.info(
                "Document parsing completed successfully",
                task_id=task_id,
                processing_time=processing_time,
                confidence_score=confidence_score,
                total_tokens=token_usage.total_tokens
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = f"Document parsing failed: {str(e)}"
            
            logger.error(
                "Document parsing failed",
                task_id=task_id,
                error=error_message,
                processing_time=processing_time
            )
            
            # Return error result
            return ParsingResult(
                task_id=task_id,
                extracted_content={},
                confidence_score=0.0,
                processing_time=processing_time,
                token_usage=TokenUsage(0, 0, 0),
                metadata={
                    'extraction_mode': extraction_mode.value,
                    'model_name': self.model_name,
                    'provider': self.llm_provider.value,
                    'error_occurred': True,
                    'processing_timestamp': time.time()
                },
                error_message=error_message
            )


class DocumentParsingService:
    """High-level service for document parsing operations."""
    
    def __init__(self, llm_provider: LLMProvider = None, model_name: str = None):
        """
        Initialize parsing service.
        
        Args:
            llm_provider: LLM provider to use (auto-detect if None)
            model_name: Model name to use (use provider default if None)
        """
        # Auto-detect provider if not specified
        if llm_provider is None:
            try:
                llm_provider = LLMClientFactory.get_default_provider()
            except Exception as e:
                logger.error("Failed to auto-detect LLM provider", error=str(e))
                raise LLMProviderError(f"No LLM provider available: {str(e)}", "unknown")
        
        self.parser = DocumentParser(llm_provider, model_name)
        logger.info(
            "Document parsing service initialized",
            provider=llm_provider.value,
            model=model_name or "default"
        )
    
    def parse_from_url(
        self,
        file_url: str,
        task_id: str,
        extraction_mode: ExtractionMode = ExtractionMode.STRUCTURED,
        custom_prompt: Optional[str] = None
    ) -> ParsingResult:
        """
        Parse document from URL with full preprocessing pipeline.
        
        Args:
            file_url: URL of document to parse
            task_id: Task ID for tracking
            extraction_mode: Mode for content extraction
            custom_prompt: Custom prompt for CUSTOM mode
            
        Returns:
            ParsingResult with extracted content
        """
        from .preprocessing import DocumentPreprocessor
        
        preprocessor = DocumentPreprocessor()
        temp_files = []
        
        try:
            # Preprocess document
            processed_doc = preprocessor.process_document(file_url)
            
            # Track temporary files for cleanup
            temp_files.extend(processed_doc.image_paths)
            
            # Parse document
            result = self.parser.parse_document(
                processed_doc, task_id, extraction_mode, custom_prompt
            )
            
            return result
            
        finally:
            # Clean up temporary files
            if temp_files:
                preprocessor.cleanup_temp_files(temp_files)