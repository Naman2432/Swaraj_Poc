import os
import uuid
import json
import csv
import traceback
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Dict, List, Optional, Any
from PIL import Image
import base64
import io

from app.log.logger import get_logger

logger = get_logger(__name__)
load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

class TechnicalDrawingExtractionService:
    def __init__(self):
        self.processed_files = {}  # In-memory storage instead of database
    
    def clean_text(self, text: str) -> str:
        """Remove non-UTF-8 characters and null bytes from text"""
        if not text:
            return ""
        
        text = text.replace('\x00', '')
        
        try:
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            text = text.encode('ascii', errors='ignore').decode('ascii')
        
        return text.strip()

    async def upload_image_to_gemini(self, image_path: str) -> Any:
        """Upload image file to Gemini"""
        try:
            logger.info(f"Uploading image file to Gemini: {image_path}")
            
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
                
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                raise ValueError("Image file is empty")
                
            uploaded_file = genai.upload_file(image_path)
            logger.info(f"Successfully uploaded image to Gemini")
            return uploaded_file
            
        except Exception as e:
            logger.error(f"Failed to upload image to Gemini: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise Exception(f"Image upload failed: {str(e)}")

    async def extract_technical_drawing_data(self, image_path: str) -> Dict:
        """Extract technical drawing data from image using Gemini"""
        try:
            logger.info(f"Starting technical drawing extraction for: {image_path}")
            
            PROMPT = """
            You are an expert technical drawing analysis system. Analyze the provided engineering drawing/diagram and extract ALL available technical information with maximum precision.

            Extraction Guidelines:
            1. Identify and extract ALL visible elements including:
               - Dimensions (linear, angular, radial, etc.)
               - Geometric features (holes, slots, threads, etc.)
               - Tolerances (geometric and dimensional)
               - Annotations, notes, and callouts
               - Material specifications
               - Surface finish requirements
               - Part numbers and identifiers
               - Revision information
               - Any tables or specification blocks
               - Special manufacturing instructions

            2. For each element, capture:
               - The exact value as shown
               - Its location/position on the drawing
               - Associated units
               - Relationships to other elements
               - Any special symbols or markings

            3. For mechanical components:
               - Identify component type (gear, bearing, etc.)
               - Extract all relevant parameters
               - Note any standard references (ISO, ANSI, etc.)

            4. Organization:
               - Group related information logically
               - Maintain hierarchy where apparent
               - Preserve all original values without interpretation

            Output Requirements:
            - Return ONLY valid JSON format
            - Include ALL extracted data - don't omit anything visible
            - Use descriptive field names based on drawing content
            - If uncertain about a value, mark as "unclear" rather than guessing
            - Preserve exact numeric values and text as shown
            - Include units for all measurements

            Important:
            - Be thorough - extract every technical detail visible
            - Don't summarize - include all raw data
            - Maintain absolute accuracy - don't modify any values
            - Focus only on technical content - ignore decorative elements

            
            """
            
            uploaded_file = await self.upload_image_to_gemini(image_path)
            
            response = model.generate_content(
                [PROMPT, uploaded_file],
                generation_config={"temperature": 0.1}
            )
            response_text = response.text.strip()
            
            # Clean up response text
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            parsed_data = json.loads(response_text)
            logger.info("Successfully parsed JSON response from Gemini")
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            logger.error(f"Response text: {response_text[:1000]}...")
            return {
                "error": f"Invalid JSON response from AI model: {str(e)}",
                "extracted_data": {}
            }
        except Exception as e:
            logger.error(f"Technical drawing extraction failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(e),
                "file": os.path.basename(image_path)
            }

    async def process_all_data(self, data: Dict, filename: str) -> List[Dict]:
        """Process all data into a flat structure for CSV output"""
        try:
            logger.info(f"Processing data for CSV output: {filename}")
            
            # Initialize with basic file info
            base_record = {
                "Filename": filename,
                "Record Type": "File Info"
            }
            
            # Flatten the JSON structure for CSV
            records = []
            
            def flatten_dict(d, parent_key='', record=None):
                if record is None:
                    record = base_record.copy()
                
                for k, v in d.items():
                    new_key = f"{parent_key}_{k}" if parent_key else k
                    
                    if isinstance(v, dict):
                        flatten_dict(v, new_key, record)
                    elif isinstance(v, list):
                        if v and isinstance(v[0], dict):
                            for i, item in enumerate(v):
                                list_record = base_record.copy()
                                list_record["Record Type"] = f"{new_key} Item {i+1}"
                                flatten_dict(item, new_key, list_record)
                                records.append(list_record)
                        else:
                            record[new_key] = "; ".join(str(x) for x in v)
                    else:
                        record[new_key] = str(v)
                
                return record
            
            main_record = flatten_dict(data)
            records.insert(0, main_record)
            
            logger.info(f"Processed {len(records)} total records")
            return records
            
        except Exception as e:
            logger.error(f"Data processing error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [{
                "Filename": filename,
                "Error": f"Data processing error: {str(e)}",
                "Record Type": "Error"
            }]

    async def process_image_file(
        self,
        task_id: str,
        file_path: str,
        output_dir: str
    ) -> Dict:
        """Process image file using Gemini extraction"""
        try:
            logger.info(f"Starting image processing for task: {task_id}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Image file not found: {file_path}")
                
            file_size = os.path.getsize(file_path)
            logger.info(f"File size: {file_size} bytes")
            
            if file_size == 0:
                raise ValueError("Image file is empty")
                
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            base_filename = os.path.join(output_dir, task_id)
            
            # Store file info in memory
            file_info = {
                "task_id": task_id,
                "original_filename": os.path.basename(file_path),
                "stored_filename": f"{task_id}_{os.path.basename(file_path)}",
                "file_path": file_path,
                "output_path": base_filename,
                "status": "processing",
                "file_size": file_size,
                "created_at": datetime.now().isoformat()
            }
            
            self.processed_files[task_id] = file_info
            
            # Extract technical drawing data
            extracted_data = await self.extract_technical_drawing_data(file_path)
            
            # Update status
            status = "completed" if "error" not in extracted_data else "completed_with_errors"
            self.processed_files[task_id]["status"] = status
            
            # Create JSON output
            json_output = {
                "task_id": task_id,
                "filename": os.path.basename(file_path),
                "file_size": file_size,
                "extracted_data": extracted_data,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            
            # Save JSON file
            json_file_path = f"{base_filename}.json"
            with open(json_file_path, "w", encoding='utf-8') as f:
                json.dump(json_output, f, indent=2, ensure_ascii=False)
            logger.info(f"JSON output saved to: {json_file_path}")
            
            # Save CSV file
            csv_file_path = f"{base_filename}.csv"
            processed_data = await self.process_all_data(extracted_data, os.path.basename(file_path))
            
            if processed_data and len(processed_data) > 0:
                with open(csv_file_path, "w", newline="", encoding='utf-8') as csvfile:
                    # Get all unique fieldnames from all records
                    fieldnames = set()
                    for record in processed_data:
                        fieldnames.update(record.keys())
                    
                    writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
                    writer.writeheader()
                    writer.writerows(processed_data)
                logger.info(f"CSV output saved to: {csv_file_path}")
            
            return {
                "status": status,
                "output_path": base_filename,
                "file_size": file_size,
                "has_errors": "error" in extracted_data,
                "json_path": json_file_path,
                "csv_path": csv_file_path
            }
            
        except FileNotFoundError as e:
            logger.error(f"File not found error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "failed",
                "error": f"File not found: {str(e)}",
                "error_type": "file_not_found"
            }
        except ValueError as e:
            logger.error(f"Value error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "failed",
                "error": f"Invalid file or data: {str(e)}",
                "error_type": "invalid_data"
            }
        except Exception as e:
            logger.error(f"Unexpected error in image processing: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "failed",
                "error": f"Processing error: {str(e)}",
                "error_type": "processing_error"
            }

    def get_file_info(self, task_id: str) -> Optional[Dict]:
        """Retrieve file information by task ID"""
        return self.processed_files.get(task_id)

    def get_all_processed_files(self) -> Dict:
        """Get all processed files"""
        return self.processed_files

    def update_file_status(self, task_id: str, status: str) -> Optional[Dict]:
        """Update file status"""
        if task_id in self.processed_files:
            self.processed_files[task_id]["status"] = status
            self.processed_files[task_id]["updated_at"] = datetime.now().isoformat()
            return self.processed_files[task_id]
        return None

    def delete_file_info(self, task_id: str) -> bool:
        """Delete file information"""
        if task_id in self.processed_files:
            del self.processed_files[task_id]
            return True
        return False