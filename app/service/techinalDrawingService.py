###########################################prompt1###########################################

# import os
# import uuid
# import json
# import csv
# import traceback
# from datetime import datetime
# from dotenv import load_dotenv
# import google.generativeai as genai
# from typing import Dict, List, Optional, Any
# from PIL import Image
# import base64
# import io

# from app.log.logger import get_logger

# logger = get_logger(__name__)
# load_dotenv()
# genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
# model = genai.GenerativeModel('gemini-2.5-flash')

# class TechnicalDrawingExtractionService:
#     def __init__(self):
#         self.processed_files = {}  # In-memory storage instead of database
    
#     def clean_text(self, text: str) -> str:
#         """Remove non-UTF-8 characters and null bytes from text"""
#         if not text:
#             return ""
        
#         text = text.replace('\x00', '')
        
#         try:
#             text = text.encode('utf-8', errors='ignore').decode('utf-8')
#         except (UnicodeEncodeError, UnicodeDecodeError):
#             text = text.encode('ascii', errors='ignore').decode('ascii')
        
#         return text.strip()

#     async def upload_image_to_gemini(self, image_path: str) -> Any:
#         """Upload image file to Gemini"""
#         try:
#             logger.info(f"Uploading image file to Gemini: {image_path}")
            
#             if not os.path.exists(image_path):
#                 raise FileNotFoundError(f"Image file not found: {image_path}")
                
#             file_size = os.path.getsize(image_path)
#             if file_size == 0:
#                 raise ValueError("Image file is empty")
                
#             uploaded_file = genai.upload_file(image_path)
#             logger.info(f"Successfully uploaded image to Gemini")
#             return uploaded_file
            
#         except Exception as e:
#             logger.error(f"Failed to upload image to Gemini: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             raise Exception(f"Image upload failed: {str(e)}")

#     async def extract_technical_drawing_data(self, image_path: str) -> Dict:
#         """Extract technical drawing data from image using Gemini"""
#         try:
#             logger.info(f"Starting technical drawing extraction for: {image_path}")
            
#             PROMPT = """
#             You are an expert technical drawing analysis system. Analyze the provided engineering drawing/diagram and extract ALL available technical information with maximum precision.

#             Extraction Guidelines:
#             1. Identify and extract ALL visible elements including:
#                - Dimensions (linear, angular, radial, etc.)
#                - Geometric features (holes, slots, threads, etc.)
#                - Tolerances (geometric and dimensional)
#                - Annotations, notes, and callouts
#                - Material specifications
#                - Surface finish requirements
#                - Part numbers and identifiers
#                - Revision information
#                - Any tables or specification blocks
#                - Special manufacturing instructions

#             2. For each element, capture:
#                - The exact value as shown
#                - Its location/position on the drawing
#                - Associated units
#                - Relationships to other elements
#                - Any special symbols or markings

#             3. For mechanical components:
#                - Identify component type (gear, bearing, etc.)
#                - Extract all relevant parameters
#                - Note any standard references (ISO, ANSI, etc.)

#             4. Organization:
#                - Group related information logically
#                - Maintain hierarchy where apparent
#                - Preserve all original values without interpretation

#             Output Requirements:
#             - Return ONLY valid JSON format
#             - Include ALL extracted data - don't omit anything visible
#             - Use descriptive field names based on drawing content
#             - If uncertain about a value, mark as "unclear" rather than guessing
#             - Preserve exact numeric values and text as shown
#             - Include units for all measurements

#             Important:
#             - Be thorough - extract every technical detail visible
#             - Don't summarize - include all raw data
#             - Maintain absolute accuracy - don't modify any values
#             - Focus only on technical content - ignore decorative elements

            
#             """
            
#             uploaded_file = await self.upload_image_to_gemini(image_path)
            
#             response = model.generate_content(
#                 [PROMPT, uploaded_file],
#                 generation_config={"temperature": 0.1}
#             )
#             response_text = response.text.strip()
            
#             # Clean up response text
#             if response_text.startswith("```json"):
#                 response_text = response_text[7:-3].strip()
#             elif response_text.startswith("```"):
#                 response_text = response_text[3:-3].strip()
            
#             parsed_data = json.loads(response_text)
#             logger.info("Successfully parsed JSON response from Gemini")
#             return parsed_data
            
#         except json.JSONDecodeError as e:
#             logger.error(f"JSON parsing error: {str(e)}")
#             logger.error(f"Response text: {response_text[:1000]}...")
#             return {
#                 "error": f"Invalid JSON response from AI model: {str(e)}",
#                 "extracted_data": {}
#             }
#         except Exception as e:
#             logger.error(f"Technical drawing extraction failed: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "error": str(e),
#                 "file": os.path.basename(image_path)
#             }

#     async def process_all_data(self, data: Dict, filename: str) -> List[Dict]:
#         """Process all data into a flat structure for CSV output"""
#         try:
#             logger.info(f"Processing data for CSV output: {filename}")
            
#             # Initialize with basic file info
#             base_record = {
#                 "Filename": filename,
#                 "Record Type": "File Info"
#             }
            
#             # Flatten the JSON structure for CSV
#             records = []
            
#             def flatten_dict(d, parent_key='', record=None):
#                 if record is None:
#                     record = base_record.copy()
                
#                 for k, v in d.items():
#                     new_key = f"{parent_key}_{k}" if parent_key else k
                    
#                     if isinstance(v, dict):
#                         flatten_dict(v, new_key, record)
#                     elif isinstance(v, list):
#                         if v and isinstance(v[0], dict):
#                             for i, item in enumerate(v):
#                                 list_record = base_record.copy()
#                                 list_record["Record Type"] = f"{new_key} Item {i+1}"
#                                 flatten_dict(item, new_key, list_record)
#                                 records.append(list_record)
#                         else:
#                             record[new_key] = "; ".join(str(x) for x in v)
#                     else:
#                         record[new_key] = str(v)
                
#                 return record
            
#             main_record = flatten_dict(data)
#             records.insert(0, main_record)
            
#             logger.info(f"Processed {len(records)} total records")
#             return records
            
#         except Exception as e:
#             logger.error(f"Data processing error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return [{
#                 "Filename": filename,
#                 "Error": f"Data processing error: {str(e)}",
#                 "Record Type": "Error"
#             }]

#     async def process_image_file(
#         self,
#         task_id: str,
#         file_path: str,
#         output_dir: str
#     ) -> Dict:
#         """Process image file using Gemini extraction"""
#         try:
#             logger.info(f"Starting image processing for task: {task_id}")
            
#             if not os.path.exists(file_path):
#                 raise FileNotFoundError(f"Image file not found: {file_path}")
                
#             file_size = os.path.getsize(file_path)
#             logger.info(f"File size: {file_size} bytes")
            
#             if file_size == 0:
#                 raise ValueError("Image file is empty")
                
#             # Create output directory
#             os.makedirs(output_dir, exist_ok=True)
#             base_filename = os.path.join(output_dir, task_id)
            
#             # Store file info in memory
#             file_info = {
#                 "task_id": task_id,
#                 "original_filename": os.path.basename(file_path),
#                 "stored_filename": f"{task_id}_{os.path.basename(file_path)}",
#                 "file_path": file_path,
#                 "output_path": base_filename,
#                 "status": "processing",
#                 "file_size": file_size,
#                 "created_at": datetime.now().isoformat()
#             }
            
#             self.processed_files[task_id] = file_info
            
#             # Extract technical drawing data
#             extracted_data = await self.extract_technical_drawing_data(file_path)
            
#             # Update status
#             status = "completed" if "error" not in extracted_data else "completed_with_errors"
#             self.processed_files[task_id]["status"] = status
            
#             # Create JSON output
#             json_output = {
#                 "task_id": task_id,
#                 "filename": os.path.basename(file_path),
#                 "file_size": file_size,
#                 "extracted_data": extracted_data,
#                 "status": status,
#                 "timestamp": datetime.now().isoformat()
#             }
            
#             # Save JSON file
#             json_file_path = f"{base_filename}.json"
#             with open(json_file_path, "w", encoding='utf-8') as f:
#                 json.dump(json_output, f, indent=2, ensure_ascii=False)
#             logger.info(f"JSON output saved to: {json_file_path}")
            
#             # Save CSV file
#             csv_file_path = f"{base_filename}.csv"
#             processed_data = await self.process_all_data(extracted_data, os.path.basename(file_path))
            
#             if processed_data and len(processed_data) > 0:
#                 with open(csv_file_path, "w", newline="", encoding='utf-8') as csvfile:
#                     # Get all unique fieldnames from all records
#                     fieldnames = set()
#                     for record in processed_data:
#                         fieldnames.update(record.keys())
                    
#                     writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
#                     writer.writeheader()
#                     writer.writerows(processed_data)
#                 logger.info(f"CSV output saved to: {csv_file_path}")
            
#             return {
#                 "status": status,
#                 "output_path": base_filename,
#                 "file_size": file_size,
#                 "has_errors": "error" in extracted_data,
#                 "json_path": json_file_path,
#                 "csv_path": csv_file_path
#             }
            
#         except FileNotFoundError as e:
#             logger.error(f"File not found error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"File not found: {str(e)}",
#                 "error_type": "file_not_found"
#             }
#         except ValueError as e:
#             logger.error(f"Value error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"Invalid file or data: {str(e)}",
#                 "error_type": "invalid_data"
#             }
#         except Exception as e:
#             logger.error(f"Unexpected error in image processing: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"Processing error: {str(e)}",
#                 "error_type": "processing_error"
#             }

#     def get_file_info(self, task_id: str) -> Optional[Dict]:
#         """Retrieve file information by task ID"""
#         return self.processed_files.get(task_id)

#     def get_all_processed_files(self) -> Dict:
#         """Get all processed files"""
#         return self.processed_files

#     def update_file_status(self, task_id: str, status: str) -> Optional[Dict]:
#         """Update file status"""
#         if task_id in self.processed_files:
#             self.processed_files[task_id]["status"] = status
#             self.processed_files[task_id]["updated_at"] = datetime.now().isoformat()
#             return self.processed_files[task_id]
#         return None

#     def delete_file_info(self, task_id: str) -> bool:
#         """Delete file information"""
#         if task_id in self.processed_files:
#             del self.processed_files[task_id]
#             return True
#         return False



###########################################prompt2###########################################



# import os
# import uuid
# import json
# import csv
# import traceback
# from datetime import datetime
# from dotenv import load_dotenv
# import google.generativeai as genai
# from typing import Dict, List, Optional, Any
# from PIL import Image
# import base64
# import io

# from app.log.logger import get_logger

# logger = get_logger(__name__)
# load_dotenv()
# genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
# model = genai.GenerativeModel('gemini-2.5-flash')

# class TechnicalDrawingExtractionService:
#     def __init__(self):
#         self.processed_files = {}  # In-memory storage instead of database
    
#     def clean_text(self, text: str) -> str:
#         """Remove non-UTF-8 characters and null bytes from text"""
#         if not text:
#             return ""
        
#         text = text.replace('\x00', '')
        
#         try:
#             text = text.encode('utf-8', errors='ignore').decode('utf-8')
#         except (UnicodeEncodeError, UnicodeDecodeError):
#             text = text.encode('ascii', errors='ignore').decode('ascii')
        
#         return text.strip()

#     async def upload_image_to_gemini(self, image_path: str) -> Any:
#         """Upload image file to Gemini"""
#         try:
#             logger.info(f"Uploading image file to Gemini: {image_path}")
            
#             if not os.path.exists(image_path):
#                 raise FileNotFoundError(f"Image file not found: {image_path}")
                
#             file_size = os.path.getsize(image_path)
#             if file_size == 0:
#                 raise ValueError("Image file is empty")
                
#             uploaded_file = genai.upload_file(image_path)
#             logger.info(f"Successfully uploaded image to Gemini")
#             return uploaded_file
            
#         except Exception as e:
#             logger.error(f"Failed to upload image to Gemini: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             raise Exception(f"Image upload failed: {str(e)}")

#     async def extract_technical_drawing_data(self, image_path: str) -> Dict:
#         """Extract technical drawing data from image using Gemini"""
#         try:
#             logger.info(f"Starting technical drawing extraction for: {image_path}")
            
#             PROMPT = """
#             You are a precision mechanical engineering analysis system specialized in gear and mechanical component technical drawings. Analyze this AutoCAD technical drawing and extract ALL visible technical specifications with absolute accuracy.

#             CRITICAL INSTRUCTIONS:
#             - Extract ONLY what is explicitly visible in the drawing
#             - Do NOT add any calculated values, interpretations, or engineering knowledge
#             - Preserve exact numeric values and units as shown
#             - If text is unclear or ambiguous, mark as "unclear_text"

#             EXTRACTION REQUIREMENTS:

#             1. GEAR SPECIFICATIONS:
#                - Number of teeth (if countable or specified)
#                - Pitch circle diameter (PCD)
#                - Outside diameter (OD) 
#                - Root diameter
#                - Tooth pitch/module values
#                - Pressure angle (if specified)
#                - Gear type classification (spur, helical, bevel, etc.)

#             2. DIMENSIONAL DATA:
#                - ALL linear dimensions with exact values and units
#                - Diameter symbols (⌀) and their values  
#                - Angular dimensions and tolerances
#                - Radial dimensions (R values)
#                - Center distances and offsets
#                - Section view dimensions

#             3. GEOMETRIC TOLERANCES:
#                - Geometric dimensioning & tolerancing (GD&T) symbols
#                - Position tolerances, concentricity, runout
#                - Surface finish symbols (Ra, Rz values)
#                - Form tolerances (flatness, straightness, etc.)

#             4. MANUFACTURING SPECIFICATIONS:
#                - Material callouts and specifications
#                - Heat treatment requirements
#                - Surface finish requirements
#                - Machining notes and callouts

#             5. DRAWING METADATA:
#                - Title block information (part name, drawing number, scale, date)
#                - Revision information and approval data
#                - Section view labels and scales
#                - Drawing standards referenced (ANSI, ISO, DIN, etc.)

#             6. TABLES AND SPECIFICATIONS:
#                - Any data tables with exact values
#                - Hole charts, bolt patterns
#                - Material property tables
#                - Manufacturing specification tables

#             7. ANNOTATIONS AND NOTES:
#                - All text annotations exactly as written
#                - Manufacturing instructions
#                - Assembly notes and callouts
#                - Special requirements or conditions

#             JSON OUTPUT STRUCTURE:
#             ```json
#             {
#                 "drawing_info": {
#                     "title": "exact title from drawing",
#                     "drawing_number": "exact number",
#                     "scale": "exact scale value",
#                     "date": "exact date",
#                     "revision": "exact revision info"
#                 },
#                 "gear_specifications": {
#                     "gear_type": "type if identifiable",
#                     "number_of_teeth": "exact count or 'not_specified'",
#                     "pitch_circle_diameter": "exact value with units",
#                     "outside_diameter": "exact value with units",
#                     "root_diameter": "exact value with units",
#                     "module_or_pitch": "exact value with units",
#                     "pressure_angle": "exact value if shown"
#                 },
#                 "dimensions": {
#                     "linear_dimensions": [
#                         {"value": "exact_value", "unit": "unit", "location": "description", "tolerance": "if_shown"}
#                     ],
#                     "diameter_dimensions": [
#                         {"symbol": "⌀", "value": "exact_value", "unit": "unit", "location": "description"}
#                     ],
#                     "angular_dimensions": [
#                         {"value": "exact_value", "unit": "degrees_or_other", "location": "description"}
#                     ]
#                 },
#                 "tolerances_and_fits": [
#                     {"type": "tolerance_type", "symbol": "exact_symbol", "value": "exact_value", "location": "description"}
#                 ],
#                 "material_specifications": {
#                     "material": "exact specification if shown",
#                     "heat_treatment": "exact requirements if shown",
#                     "surface_finish": "exact values if shown"
#                 },
#                 "manufacturing_notes": [
#                     {"note": "exact text", "location": "description"}
#                 ],
#                 "section_views": {
#                     "section_labels": ["exact labels"],
#                     "section_scales": ["exact scales"],
#                     "section_dimensions": "dimensions specific to sections"
#                 },
#                 "tables_and_charts": [
#                     {"table_name": "exact name", "data": "structured table data"}
#                 ]
#             }
#             ```

#             ACCURACY REQUIREMENTS:
#             - Measure and record ALL visible dimensions exactly as shown
#             - Include all decimal places as displayed
#             - Note any dimension lines, extension lines, and their values
#             - Record tolerances exactly as notated (+/-, ±, geometric symbols)
#             - Capture all text exactly as written, including abbreviations
#             - If a value appears multiple times, record each instance

#             Extract everything visible - this is for precision manufacturing documentation.
#             """
            
#             uploaded_file = await self.upload_image_to_gemini(image_path)
            
#             response = model.generate_content(
#                 [PROMPT, uploaded_file],
#                 generation_config={"temperature": 0.0}  # Reduced to 0.0 for maximum consistency
#             )
#             response_text = response.text.strip()
            
#             # Clean up response text
#             if response_text.startswith("```json"):
#                 response_text = response_text[7:-3].strip()
#             elif response_text.startswith("```"):
#                 response_text = response_text[3:-3].strip()
            
#             parsed_data = json.loads(response_text)
#             logger.info("Successfully parsed JSON response from Gemini")
#             return parsed_data
            
#         except json.JSONDecodeError as e:
#             logger.error(f"JSON parsing error: {str(e)}")
#             logger.error(f"Response text: {response_text[:1000]}...")
#             return {
#                 "error": f"Invalid JSON response from AI model: {str(e)}",
#                 "extracted_data": {}
#             }
#         except Exception as e:
#             logger.error(f"Technical drawing extraction failed: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "error": str(e),
#                 "file": os.path.basename(image_path)
#             }

#     async def process_all_data(self, data: Dict, filename: str) -> List[Dict]:
#         """Process all data into a flat structure for CSV output with gear-specific organization"""
#         try:
#             logger.info(f"Processing data for CSV output: {filename}")
            
#             records = []
            
#             # Create separate records for different data types
#             def create_gear_records(data, filename):
#                 gear_records = []
                
#                 # Basic drawing info record
#                 if "drawing_info" in data:
#                     drawing_record = {
#                         "Filename": filename,
#                         "Record_Type": "Drawing_Info",
#                         **{f"Drawing_{k}": v for k, v in data["drawing_info"].items()}
#                     }
#                     gear_records.append(drawing_record)
                
#                 # Gear specifications record
#                 if "gear_specifications" in data:
#                     gear_record = {
#                         "Filename": filename,
#                         "Record_Type": "Gear_Specifications",
#                         **{f"Gear_{k}": v for k, v in data["gear_specifications"].items()}
#                     }
#                     gear_records.append(gear_record)
                
#                 # Dimension records (one per dimension)
#                 if "dimensions" in data:
#                     for dim_type, dimensions in data["dimensions"].items():
#                         if isinstance(dimensions, list):
#                             for i, dim in enumerate(dimensions):
#                                 dim_record = {
#                                     "Filename": filename,
#                                     "Record_Type": f"Dimension_{dim_type}",
#                                     "Dimension_Index": i + 1,
#                                     **{f"Dim_{k}": v for k, v in dim.items()}
#                                 }
#                                 gear_records.append(dim_record)
                
#                 # Tolerance records
#                 if "tolerances_and_fits" in data and isinstance(data["tolerances_and_fits"], list):
#                     for i, tol in enumerate(data["tolerances_and_fits"]):
#                         tol_record = {
#                             "Filename": filename,
#                             "Record_Type": "Tolerance",
#                             "Tolerance_Index": i + 1,
#                             **{f"Tol_{k}": v for k, v in tol.items()}
#                         }
#                         gear_records.append(tol_record)
                
#                 # Material specifications
#                 if "material_specifications" in data:
#                     material_record = {
#                         "Filename": filename,
#                         "Record_Type": "Material_Specifications",
#                         **{f"Material_{k}": v for k, v in data["material_specifications"].items()}
#                     }
#                     gear_records.append(material_record)
                
#                 # Manufacturing notes
#                 if "manufacturing_notes" in data and isinstance(data["manufacturing_notes"], list):
#                     for i, note in enumerate(data["manufacturing_notes"]):
#                         note_record = {
#                             "Filename": filename,
#                             "Record_Type": "Manufacturing_Note",
#                             "Note_Index": i + 1,
#                             **{f"Note_{k}": v for k, v in note.items()}
#                         }
#                         gear_records.append(note_record)
                
#                 return gear_records
            
#             records = create_gear_records(data, filename)
            
#             # If no structured records were created, fall back to flattened approach
#             if not records:
#                 def flatten_dict(d, parent_key='', record=None):
#                     if record is None:
#                         record = {"Filename": filename, "Record_Type": "General"}
                    
#                     for k, v in d.items():
#                         new_key = f"{parent_key}_{k}" if parent_key else k
                        
#                         if isinstance(v, dict):
#                             flatten_dict(v, new_key, record)
#                         elif isinstance(v, list):
#                             if v and isinstance(v[0], dict):
#                                 for i, item in enumerate(v):
#                                     list_record = {"Filename": filename, "Record_Type": f"{new_key}_Item_{i+1}"}
#                                     flatten_dict(item, new_key, list_record)
#                                     records.append(list_record)
#                             else:
#                                 record[new_key] = "; ".join(str(x) for x in v)
#                         else:
#                             record[new_key] = str(v)
                    
#                     return record
                
#                 main_record = flatten_dict(data)
#                 records.append(main_record)
            
#             logger.info(f"Processed {len(records)} total records")
#             return records
            
#         except Exception as e:
#             logger.error(f"Data processing error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return [{
#                 "Filename": filename,
#                 "Error": f"Data processing error: {str(e)}",
#                 "Record_Type": "Error"
#             }]

#     async def process_image_file(
#         self,
#         task_id: str,
#         file_path: str,
#         output_dir: str
#     ) -> Dict:
#         """Process image file using Gemini extraction"""
#         try:
#             logger.info(f"Starting image processing for task: {task_id}")
            
#             if not os.path.exists(file_path):
#                 raise FileNotFoundError(f"Image file not found: {file_path}")
                
#             file_size = os.path.getsize(file_path)
#             logger.info(f"File size: {file_size} bytes")
            
#             if file_size == 0:
#                 raise ValueError("Image file is empty")
                
#             # Create output directory
#             os.makedirs(output_dir, exist_ok=True)
#             base_filename = os.path.join(output_dir, task_id)
            
#             # Store file info in memory
#             file_info = {
#                 "task_id": task_id,
#                 "original_filename": os.path.basename(file_path),
#                 "stored_filename": f"{task_id}_{os.path.basename(file_path)}",
#                 "file_path": file_path,
#                 "output_path": base_filename,
#                 "status": "processing",
#                 "file_size": file_size,
#                 "created_at": datetime.now().isoformat()
#             }
            
#             self.processed_files[task_id] = file_info
            
#             # Extract technical drawing data
#             extracted_data = await self.extract_technical_drawing_data(file_path)
            
#             # Update status
#             status = "completed" if "error" not in extracted_data else "completed_with_errors"
#             self.processed_files[task_id]["status"] = status
            
#             # Create JSON output
#             json_output = {
#                 "task_id": task_id,
#                 "filename": os.path.basename(file_path),
#                 "file_size": file_size,
#                 "extracted_data": extracted_data,
#                 "status": status,
#                 "timestamp": datetime.now().isoformat()
#             }
            
#             # Save JSON file
#             json_file_path = f"{base_filename}.json"
#             with open(json_file_path, "w", encoding='utf-8') as f:
#                 json.dump(json_output, f, indent=2, ensure_ascii=False)
#             logger.info(f"JSON output saved to: {json_file_path}")
            
#             # Save CSV file
#             csv_file_path = f"{base_filename}.csv"
#             processed_data = await self.process_all_data(extracted_data, os.path.basename(file_path))
            
#             if processed_data and len(processed_data) > 0:
#                 with open(csv_file_path, "w", newline="", encoding='utf-8') as csvfile:
#                     # Get all unique fieldnames from all records
#                     fieldnames = set()
#                     for record in processed_data:
#                         fieldnames.update(record.keys())
                    
#                     writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
#                     writer.writeheader()
#                     writer.writerows(processed_data)
#                 logger.info(f"CSV output saved to: {csv_file_path}")
            
#             return {
#                 "status": status,
#                 "output_path": base_filename,
#                 "file_size": file_size,
#                 "has_errors": "error" in extracted_data,
#                 "json_path": json_file_path,
#                 "csv_path": csv_file_path
#             }
            
#         except FileNotFoundError as e:
#             logger.error(f"File not found error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"File not found: {str(e)}",
#                 "error_type": "file_not_found"
#             }
#         except ValueError as e:
#             logger.error(f"Value error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"Invalid file or data: {str(e)}",
#                 "error_type": "invalid_data"
#             }
#         except Exception as e:
#             logger.error(f"Unexpected error in image processing: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"Processing error: {str(e)}",
#                 "error_type": "processing_error"
#             }

#     def get_file_info(self, task_id: str) -> Optional[Dict]:
#         """Retrieve file information by task ID"""
#         return self.processed_files.get(task_id)

#     def get_all_processed_files(self) -> Dict:
#         """Get all processed files"""
#         return self.processed_files

#     def update_file_status(self, task_id: str, status: str) -> Optional[Dict]:
#         """Update file status"""
#         if task_id in self.processed_files:
#             self.processed_files[task_id]["status"] = status
#             self.processed_files[task_id]["updated_at"] = datetime.now().isoformat()
#             return self.processed_files[task_id]
#         return None

#     def delete_file_info(self, task_id: str) -> bool:
#         """Delete file information"""
#         if task_id in self.processed_files:
#             del self.processed_files[task_id]
#             return True
#         return False

###########################################prompt3###########################################

# import os
# import uuid
# import json
# import csv
# import traceback
# from datetime import datetime
# from dotenv import load_dotenv
# import google.generativeai as genai
# from typing import Dict, List, Optional, Any
# from PIL import Image
# import base64
# import io

# from app.log.logger import get_logger

# logger = get_logger(__name__)
# load_dotenv()
# genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
# model = genai.GenerativeModel('gemini-2.5-flash')

# class TechnicalDrawingExtractionService:
#     def __init__(self):
#         self.processed_files = {}  # In-memory storage instead of database
    
#     def clean_text(self, text: str) -> str:
#         """Remove non-UTF-8 characters and null bytes from text"""
#         if not text:
#             return ""
        
#         text = text.replace('\x00', '')
        
#         try:
#             text = text.encode('utf-8', errors='ignore').decode('utf-8')
#         except (UnicodeEncodeError, UnicodeDecodeError):
#             text = text.encode('ascii', errors='ignore').decode('ascii')
        
#         return text.strip()

#     async def upload_image_to_gemini(self, image_path: str) -> Any:
#         """Upload image file to Gemini"""
#         try:
#             logger.info(f"Uploading image file to Gemini: {image_path}")
            
#             if not os.path.exists(image_path):
#                 raise FileNotFoundError(f"Image file not found: {image_path}")
                
#             file_size = os.path.getsize(image_path)
#             if file_size == 0:
#                 raise ValueError("Image file is empty")
                
#             uploaded_file = genai.upload_file(image_path)
#             logger.info(f"Successfully uploaded image to Gemini")
#             return uploaded_file
            
#         except Exception as e:
#             logger.error(f"Failed to upload image to Gemini: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             raise Exception(f"Image upload failed: {str(e)}")

#     async def extract_technical_drawing_data(self, image_path: str) -> Dict:
#         """Extract technical drawing data from image using Gemini"""
#         try:
#             logger.info(f"Starting technical drawing extraction for: {image_path}")
            
#             PROMPT = """
#             You are an expert gear engineering analysis system with comprehensive knowledge of involute gear geometry, AGMA standards, ISO gear specifications, and precision manufacturing requirements. Analyze this technical gear drawing with absolute precision and extract ALL visible specifications.

#             CRITICAL EXTRACTION PROTOCOL:
#             - Extract ONLY explicitly visible values - NO calculations or derivations
#             - Preserve exact numeric values, decimal places, and units as displayed
#             - Record dimension symbols (⌀, R, ±) exactly as shown
#             - Mark unclear text as "unclear_text" rather than guessing
#             - Focus on manufacturing-critical dimensions and tolerances

#             ADVANCED GEAR SPECIFICATION EXTRACTION:

#             1. PRIMARY GEAR GEOMETRY:
#                - Number of teeth (Z) - count if visible or extract from specifications
#                - Outside diameter (Da) - tip diameter/major diameter
#                - Pitch circle diameter (D) - reference diameter for tooth spacing
#                - Root diameter (Df) - minor diameter at tooth root
#                - Base circle diameter (Db) - fundamental to involute profile
#                - Addendum (ha) - radial distance from pitch circle to tip
#                - Dedendum (hf) - radial distance from pitch circle to root
#                - Whole depth (h) - total tooth height
#                - Working depth - engagement depth between mating gears

#             2. TOOTH GEOMETRY PARAMETERS:
#                - Module (m) or Diametral Pitch (Pd) - fundamental tooth size
#                - Pressure angle (α) - standard values 14.5°, 20°, 25°
#                - Tooth thickness (s) - arc thickness at pitch circle
#                - Space width - arc width between teeth at pitch circle
#                - Backlash allowance - clearance specifications
#                - Tip relief - modification at tooth tips
#                - Root fillet radius - transition radius at tooth root

#             3. GEAR BODY DIMENSIONS:
#                - Hub diameter and length - central mounting portion
#                - Web thickness - connecting section between hub and rim
#                - Rim thickness - gear tooth supporting structure
#                - Face width (b) - axial length of teeth
#                - Keyway dimensions - width, depth, length, tolerances
#                - Bore diameter and tolerance - shaft mounting hole
#                - Shoulder diameters - stepped shaft interfaces

#             4. MANUFACTURING TOLERANCES & QUALITY:
#                - AGMA quality class (if specified)
#                - DIN quality grade (if specified) 
#                - Tooth-to-tooth composite tolerance
#                - Total composite tolerance
#                - Runout tolerances (radial, axial)
#                - Concentricity requirements
#                - Profile tolerance - involute form accuracy
#                - Lead tolerance - tooth alignment accuracy
#                - Pitch tolerance - tooth spacing accuracy

#             5. SURFACE SPECIFICATIONS:
#                - Surface roughness (Ra, Rz) for tooth flanks
#                - Surface roughness for bore and mounting surfaces
#                - Heat treatment specifications (case hardening depth, core hardness)
#                - Material specifications (steel grade, properties)
#                - Coating requirements (if any)

#             6. INSPECTION DIMENSIONS:
#                - Measurement over pins/balls diameter
#                - Span measurement (across multiple teeth)
#                - Chordal thickness and height
#                - Base tangent length
#                - Functional gauge dimensions

#             7. SECTION VIEW ANALYSIS:
#                - Cross-sectional dimensions from section cuts
#                - Internal features (lightening holes, ribs)
#                - Wall thickness variations
#                - Transition radii and chamfers
#                - Assembly interfaces and mating surfaces

#             ENHANCED JSON OUTPUT STRUCTURE:
#             ```json
#             {
#                 "drawing_metadata": {
#                     "part_name": "exact title",
#                     "drawing_number": "exact number",
#                     "scale": "exact scale",
#                     "date": "exact date",
#                     "revision": "revision level",
#                     "standard_reference": "AGMA/ISO/DIN standard if shown",
#                     "material_specification": "exact material callout"
#                 },
#                 "gear_fundamental_parameters": {
#                     "gear_type": "spur/helical/bevel/worm/etc",
#                     "number_of_teeth": "exact count",
#                     "module_or_pitch": {"value": "number", "unit": "mm or inch", "type": "module or diametral_pitch"},
#                     "pressure_angle": {"value": "degrees", "location": "where_specified"},
#                     "helix_angle": "degrees if helical gear",
#                     "hand_of_helix": "LH/RH if specified"
#                 },
#                 "gear_diameters": {
#                     "outside_diameter": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
#                     "pitch_diameter": {"value": "calculated or specified", "unit": "mm/inch"},
#                     "root_diameter": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
#                     "base_diameter": {"value": "if_specified", "unit": "mm/inch"},
#                     "bore_diameter": {"value": "exact_value", "unit": "mm/inch", "tolerance": "fit_specification"}
#                 },
#                 "tooth_geometry": {
#                     "addendum": {"value": "if_specified", "unit": "mm/inch"},
#                     "dedendum": {"value": "if_specified", "unit": "mm/inch"},
#                     "whole_depth": {"value": "if_specified", "unit": "mm/inch"},
#                     "face_width": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
#                     "tooth_thickness": {"value": "if_specified", "unit": "mm/inch", "measurement_method": "arc/normal/chordal"}
#                 },
#                 "gear_body_dimensions": {
#                     "hub_diameter": {"value": "exact_value", "unit": "mm/inch"},
#                     "hub_length": {"value": "exact_value", "unit": "mm/inch"},
#                     "web_thickness": {"value": "exact_value", "unit": "mm/inch"},
#                     "rim_thickness": {"value": "exact_value", "unit": "mm/inch"},
#                     "overall_length": {"value": "exact_value", "unit": "mm/inch"}
#                 },
#                 "keyway_specifications": {
#                     "width": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
#                     "depth": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
#                     "length": {"value": "exact_value", "unit": "mm/inch"},
#                     "key_standard": "DIN6885/ANSI_standard if referenced"
#                 },
#                 "geometric_tolerances": [
#                     {"feature": "description", "tolerance_type": "runout/concentricity/etc", "value": "exact_value", "datum": "reference_datum"}
#                 ],
#                 "surface_specifications": {
#                     "tooth_surface_finish": {"value": "Ra/Rz_value", "unit": "micrometers/microinches"},
#                     "bore_surface_finish": {"value": "Ra/Rz_value", "unit": "micrometers/microinches"},
#                     "material": "exact material specification",
#                     "heat_treatment": "exact treatment specification",
#                     "hardness": "HRC/HB value if specified"
#                 },
#                 "quality_specifications": {
#                     "agma_quality_class": "if_specified",
#                     "din_quality_grade": "if_specified", 
#                     "inspection_requirements": ["list of special requirements"]
#                 },
#                 "manufacturing_notes": [
#                     {"note": "exact_text", "location": "drawing_location", "type": "machining/assembly/inspection"}
#                 ],
#                 "section_view_data": {
#                     "section_identifier": "A-A/B-B/etc",
#                     "section_scale": "exact_scale",
#                     "section_dimensions": [
#                         {"feature": "description", "value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"}
#                     ]
#                 },
#                 "specification_tables": [
#                     {"table_name": "exact_name", "table_data": "structured_data_from_table"}
#                 ]
#             }
#             ```

#             PRECISION REQUIREMENTS:
#             - Record ALL dimension values with exact decimal precision as shown
#             - Capture all tolerance notations (+0.000/-0.000, ±0.000, H7/g6, etc.)
#             - Extract complete GD&T symbols with datum references
#             - Note all surface finish symbols and values (32√, Ra 1.6, etc.)
#             - Record material specifications exactly (AISI 4140, SAE 1045, etc.)
#             - Capture heat treatment callouts precisely (58-62 HRC, through hardened, etc.)

#             This is for precision gear manufacturing - extract every technical detail visible for machining and quality control.
#             """
            
#             uploaded_file = await self.upload_image_to_gemini(image_path)
            
#             response = model.generate_content(
#                 [PROMPT, uploaded_file],
#                 generation_config={"temperature": 0.0}  # Reduced to 0.0 for maximum consistency
#             )
#             response_text = response.text.strip()
            
#             # Clean up response text
#             if response_text.startswith("```json"):
#                 response_text = response_text[7:-3].strip()
#             elif response_text.startswith("```"):
#                 response_text = response_text[3:-3].strip()
            
#             parsed_data = json.loads(response_text)
#             logger.info("Successfully parsed JSON response from Gemini")
#             return parsed_data
            
#         except json.JSONDecodeError as e:
#             logger.error(f"JSON parsing error: {str(e)}")
#             logger.error(f"Response text: {response_text[:1000]}...")
#             return {
#                 "error": f"Invalid JSON response from AI model: {str(e)}",
#                 "extracted_data": {}
#             }
#         except Exception as e:
#             logger.error(f"Technical drawing extraction failed: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "error": str(e),
#                 "file": os.path.basename(image_path)
#             }

#     async def process_all_data(self, data: Dict, filename: str) -> List[Dict]:
#         """Process all data into a flat structure for CSV output with gear-specific organization"""
#         try:
#             logger.info(f"Processing data for CSV output: {filename}")
            
#             records = []
            
#             # Create separate records for different data types
#             def create_gear_records(data, filename):
#                 gear_records = []
                
#                 # Basic drawing info record
#                 if "drawing_info" in data:
#                     drawing_record = {
#                         "Filename": filename,
#                         "Record_Type": "Drawing_Info",
#                         **{f"Drawing_{k}": v for k, v in data["drawing_info"].items()}
#                     }
#                     gear_records.append(drawing_record)
                
#                 # Gear specifications record
#                 if "gear_specifications" in data:
#                     gear_record = {
#                         "Filename": filename,
#                         "Record_Type": "Gear_Specifications",
#                         **{f"Gear_{k}": v for k, v in data["gear_specifications"].items()}
#                     }
#                     gear_records.append(gear_record)
                
#                 # Dimension records (one per dimension)
#                 if "dimensions" in data:
#                     for dim_type, dimensions in data["dimensions"].items():
#                         if isinstance(dimensions, list):
#                             for i, dim in enumerate(dimensions):
#                                 dim_record = {
#                                     "Filename": filename,
#                                     "Record_Type": f"Dimension_{dim_type}",
#                                     "Dimension_Index": i + 1,
#                                     **{f"Dim_{k}": v for k, v in dim.items()}
#                                 }
#                                 gear_records.append(dim_record)
                
#                 # Tolerance records
#                 if "tolerances_and_fits" in data and isinstance(data["tolerances_and_fits"], list):
#                     for i, tol in enumerate(data["tolerances_and_fits"]):
#                         tol_record = {
#                             "Filename": filename,
#                             "Record_Type": "Tolerance",
#                             "Tolerance_Index": i + 1,
#                             **{f"Tol_{k}": v for k, v in tol.items()}
#                         }
#                         gear_records.append(tol_record)
                
#                 # Material specifications
#                 if "material_specifications" in data:
#                     material_record = {
#                         "Filename": filename,
#                         "Record_Type": "Material_Specifications",
#                         **{f"Material_{k}": v for k, v in data["material_specifications"].items()}
#                     }
#                     gear_records.append(material_record)
                
#                 # Manufacturing notes
#                 if "manufacturing_notes" in data and isinstance(data["manufacturing_notes"], list):
#                     for i, note in enumerate(data["manufacturing_notes"]):
#                         note_record = {
#                             "Filename": filename,
#                             "Record_Type": "Manufacturing_Note",
#                             "Note_Index": i + 1,
#                             **{f"Note_{k}": v for k, v in note.items()}
#                         }
#                         gear_records.append(note_record)
                
#                 return gear_records
            
#             records = create_gear_records(data, filename)
            
#             # If no structured records were created, fall back to flattened approach
#             if not records:
#                 def flatten_dict(d, parent_key='', record=None):
#                     if record is None:
#                         record = {"Filename": filename, "Record_Type": "General"}
                    
#                     for k, v in d.items():
#                         new_key = f"{parent_key}_{k}" if parent_key else k
                        
#                         if isinstance(v, dict):
#                             flatten_dict(v, new_key, record)
#                         elif isinstance(v, list):
#                             if v and isinstance(v[0], dict):
#                                 for i, item in enumerate(v):
#                                     list_record = {"Filename": filename, "Record_Type": f"{new_key}_Item_{i+1}"}
#                                     flatten_dict(item, new_key, list_record)
#                                     records.append(list_record)
#                             else:
#                                 record[new_key] = "; ".join(str(x) for x in v)
#                         else:
#                             record[new_key] = str(v)
                    
#                     return record
                
#                 main_record = flatten_dict(data)
#                 records.append(main_record)
            
#             logger.info(f"Processed {len(records)} total records")
#             return records
            
#         except Exception as e:
#             logger.error(f"Data processing error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return [{
#                 "Filename": filename,
#                 "Error": f"Data processing error: {str(e)}",
#                 "Record_Type": "Error"
#             }]

#     async def process_image_file(
#         self,
#         task_id: str,
#         file_path: str,
#         output_dir: str
#     ) -> Dict:
#         """Process image file using Gemini extraction"""
#         try:
#             logger.info(f"Starting image processing for task: {task_id}")
            
#             if not os.path.exists(file_path):
#                 raise FileNotFoundError(f"Image file not found: {file_path}")
                
#             file_size = os.path.getsize(file_path)
#             logger.info(f"File size: {file_size} bytes")
            
#             if file_size == 0:
#                 raise ValueError("Image file is empty")
                
#             # Create output directory
#             os.makedirs(output_dir, exist_ok=True)
#             base_filename = os.path.join(output_dir, task_id)
            
#             # Store file info in memory
#             file_info = {
#                 "task_id": task_id,
#                 "original_filename": os.path.basename(file_path),
#                 "stored_filename": f"{task_id}_{os.path.basename(file_path)}",
#                 "file_path": file_path,
#                 "output_path": base_filename,
#                 "status": "processing",
#                 "file_size": file_size,
#                 "created_at": datetime.now().isoformat()
#             }
            
#             self.processed_files[task_id] = file_info
            
#             # Extract technical drawing data
#             extracted_data = await self.extract_technical_drawing_data(file_path)
            
#             # Update status
#             status = "completed" if "error" not in extracted_data else "completed_with_errors"
#             self.processed_files[task_id]["status"] = status
            
#             # Create JSON output
#             json_output = {
#                 "task_id": task_id,
#                 "filename": os.path.basename(file_path),
#                 "file_size": file_size,
#                 "extracted_data": extracted_data,
#                 "status": status,
#                 "timestamp": datetime.now().isoformat()
#             }
            
#             # Save JSON file
#             json_file_path = f"{base_filename}.json"
#             with open(json_file_path, "w", encoding='utf-8') as f:
#                 json.dump(json_output, f, indent=2, ensure_ascii=False)
#             logger.info(f"JSON output saved to: {json_file_path}")
            
#             # Save CSV file
#             csv_file_path = f"{base_filename}.csv"
#             processed_data = await self.process_all_data(extracted_data, os.path.basename(file_path))
            
#             if processed_data and len(processed_data) > 0:
#                 with open(csv_file_path, "w", newline="", encoding='utf-8') as csvfile:
#                     # Get all unique fieldnames from all records
#                     fieldnames = set()
#                     for record in processed_data:
#                         fieldnames.update(record.keys())
                    
#                     writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
#                     writer.writeheader()
#                     writer.writerows(processed_data)
#                 logger.info(f"CSV output saved to: {csv_file_path}")
            
#             return {
#                 "status": status,
#                 "output_path": base_filename,
#                 "file_size": file_size,
#                 "has_errors": "error" in extracted_data,
#                 "json_path": json_file_path,
#                 "csv_path": csv_file_path
#             }
            
#         except FileNotFoundError as e:
#             logger.error(f"File not found error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"File not found: {str(e)}",
#                 "error_type": "file_not_found"
#             }
#         except ValueError as e:
#             logger.error(f"Value error: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"Invalid file or data: {str(e)}",
#                 "error_type": "invalid_data"
#             }
#         except Exception as e:
#             logger.error(f"Unexpected error in image processing: {str(e)}")
#             logger.error(f"Traceback: {traceback.format_exc()}")
#             return {
#                 "status": "failed",
#                 "error": f"Processing error: {str(e)}",
#                 "error_type": "processing_error"
#             }

#     def get_file_info(self, task_id: str) -> Optional[Dict]:
#         """Retrieve file information by task ID"""
#         return self.processed_files.get(task_id)

#     def get_all_processed_files(self) -> Dict:
#         """Get all processed files"""
#         return self.processed_files

#     def update_file_status(self, task_id: str, status: str) -> Optional[Dict]:
#         """Update file status"""
#         if task_id in self.processed_files:
#             self.processed_files[task_id]["status"] = status
#             self.processed_files[task_id]["updated_at"] = datetime.now().isoformat()
#             return self.processed_files[task_id]
#         return None

#     def delete_file_info(self, task_id: str) -> bool:
#         """Delete file information"""
#         if task_id in self.processed_files:
#             del self.processed_files[task_id]
#             return True
#         return False


###########################################ratelimit###########################################


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

    def count_tokens_accurate(self, text: str) -> int:
        """
        More accurate token counting using Gemini's count_tokens method.
        Falls back to improved estimation if API call fails.
        """
        try:
            if not text:
                return 0
            
            # Use Gemini's actual token counting
            token_count = model.count_tokens(text)
            return token_count.total_tokens
            
        except Exception as e:
            logger.warning(f"Failed to get accurate token count, using estimation: {str(e)}")
            return self.estimate_tokens(text)
    
    def estimate_tokens(self, text: str) -> int:
        """
        Improved token estimation for Gemini models.
        Based on analysis that Gemini tokenization is closer to:
        - ~3.5-4 characters per token for English
        - Technical terms and numbers may have different ratios
        """
        if not text:
            return 0
        
        # More sophisticated estimation
        words = text.split()
        chars = len(text)
        
        # Base estimation: 3.5 chars per token for mixed content
        base_tokens = chars / 3.5
        
        # Adjust for technical content (more precise numbers, symbols)
        technical_chars = sum(1 for c in text if c in '()[]{}+-=<>≥≤±∅°')
        if technical_chars > chars * 0.1:  # If >10% technical characters
            base_tokens = chars / 3.0  # Technical content uses more tokens
        
        return int(base_tokens)

    def estimate_image_tokens(self, image_path: str) -> int:
        """
        Estimate tokens consumed by an image.
        Gemini's image token consumption depends on image size and resolution.
        """
        try:
            if not os.path.exists(image_path):
                return 0
            
            with Image.open(image_path) as img:
                width, height = img.size
                
            # Gemini's token consumption is roughly based on image dimensions
            # This is an approximation - actual consumption may vary
            pixels = width * height
            
            # Rough estimation based on Gemini documentation
            if pixels <= 512 * 512:
                return 258  # Small images
            elif pixels <= 1024 * 1024:
                return 516  # Medium images
            else:
                # Large images are resized, but still consume more tokens
                return 774  # Large images
                
        except Exception as e:
            logger.warning(f"Could not estimate image tokens: {str(e)}")
            return 500  # Default estimate
    
    def count_total_tokens_for_request(self, prompt: str, image_path: str = None) -> Dict[str, int]:
        """
        Count total tokens for a complete request including prompt and image.
        """
        prompt_tokens = self.count_tokens_accurate(prompt)
        image_tokens = self.estimate_image_tokens(image_path) if image_path else 0
        
        return {
            "prompt_tokens": prompt_tokens,
            "image_tokens": image_tokens,
            "total_input_tokens": prompt_tokens + image_tokens
        }

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
            You are an expert gear engineering analysis system with comprehensive knowledge of involute gear geometry, AGMA standards, ISO gear specifications, and precision manufacturing requirements. Analyze this technical gear drawing with absolute precision and extract ALL visible specifications.

            CRITICAL EXTRACTION PROTOCOL:
            - Extract ONLY explicitly visible values - NO calculations or derivations
            - Preserve exact numeric values, decimal places, and units as displayed
            - Record dimension symbols (⌀, R, ±) exactly as shown
            - Mark unclear text as "unclear_text" rather than guessing
            - Focus on manufacturing-critical dimensions and tolerances

            ADVANCED GEAR SPECIFICATION EXTRACTION:

            1. PRIMARY GEAR GEOMETRY:
               - Number of teeth (Z) - count if visible or extract from specifications
               - Outside diameter (Da) - tip diameter/major diameter
               - Pitch circle diameter (D) - reference diameter for tooth spacing
               - Root diameter (Df) - minor diameter at tooth root
               - Base circle diameter (Db) - fundamental to involute profile
               - Addendum (ha) - radial distance from pitch circle to tip
               - Dedendum (hf) - radial distance from pitch circle to root
               - Whole depth (h) - total tooth height
               - Working depth - engagement depth between mating gears

            2. TOOTH GEOMETRY PARAMETERS:
               - Module (m) or Diametral Pitch (Pd) - fundamental tooth size
               - Pressure angle (α) - standard values 14.5°, 20°, 25°
               - Tooth thickness (s) - arc thickness at pitch circle
               - Space width - arc width between teeth at pitch circle
               - Backlash allowance - clearance specifications
               - Tip relief - modification at tooth tips
               - Root fillet radius - transition radius at tooth root

            3. GEAR BODY DIMENSIONS:
               - Hub diameter and length - central mounting portion
               - Web thickness - connecting section between hub and rim
               - Rim thickness - gear tooth supporting structure
               - Face width (b) - axial length of teeth
               - Keyway dimensions - width, depth, length, tolerances
               - Bore diameter and tolerance - shaft mounting hole
               - Shoulder diameters - stepped shaft interfaces

            4. MANUFACTURING TOLERANCES & QUALITY:
               - AGMA quality class (if specified)
               - DIN quality grade (if specified) 
               - Tooth-to-tooth composite tolerance
               - Total composite tolerance
               - Runout tolerances (radial, axial)
               - Concentricity requirements
               - Profile tolerance - involute form accuracy
               - Lead tolerance - tooth alignment accuracy
               - Pitch tolerance - tooth spacing accuracy

            5. SURFACE SPECIFICATIONS:
               - Surface roughness (Ra, Rz) for tooth flanks
               - Surface roughness for bore and mounting surfaces
               - Heat treatment specifications (case hardening depth, core hardness)
               - Material specifications (steel grade, properties)
               - Coating requirements (if any)

            6. INSPECTION DIMENSIONS:
               - Measurement over pins/balls diameter
               - Span measurement (across multiple teeth)
               - Chordal thickness and height
               - Base tangent length
               - Functional gauge dimensions

            7. SECTION VIEW ANALYSIS:
               - Cross-sectional dimensions from section cuts
               - Internal features (lightening holes, ribs)
               - Wall thickness variations
               - Transition radii and chamfers
               - Assembly interfaces and mating surfaces

            ENHANCED JSON OUTPUT STRUCTURE:
            ```json
            {
                "drawing_metadata": {
                    "part_name": "exact title",
                    "drawing_number": "exact number",
                    "scale": "exact scale",
                    "date": "exact date",
                    "revision": "revision level",
                    "standard_reference": "AGMA/ISO/DIN standard if shown",
                    "material_specification": "exact material callout"
                },
                "gear_fundamental_parameters": {
                    "gear_type": "spur/helical/bevel/worm/etc",
                    "number_of_teeth": "exact count",
                    "module_or_pitch": {"value": "number", "unit": "mm or inch", "type": "module or diametral_pitch"},
                    "pressure_angle": {"value": "degrees", "location": "where_specified"},
                    "helix_angle": "degrees if helical gear",
                    "hand_of_helix": "LH/RH if specified"
                },
                "gear_diameters": {
                    "outside_diameter": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
                    "pitch_diameter": {"value": "calculated or specified", "unit": "mm/inch"},
                    "root_diameter": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
                    "base_diameter": {"value": "if_specified", "unit": "mm/inch"},
                    "bore_diameter": {"value": "exact_value", "unit": "mm/inch", "tolerance": "fit_specification"}
                },
                "tooth_geometry": {
                    "addendum": {"value": "if_specified", "unit": "mm/inch"},
                    "dedendum": {"value": "if_specified", "unit": "mm/inch"},
                    "whole_depth": {"value": "if_specified", "unit": "mm/inch"},
                    "face_width": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
                    "tooth_thickness": {"value": "if_specified", "unit": "mm/inch", "measurement_method": "arc/normal/chordal"}
                },
                "gear_body_dimensions": {
                    "hub_diameter": {"value": "exact_value", "unit": "mm/inch"},
                    "hub_length": {"value": "exact_value", "unit": "mm/inch"},
                    "web_thickness": {"value": "exact_value", "unit": "mm/inch"},
                    "rim_thickness": {"value": "exact_value", "unit": "mm/inch"},
                    "overall_length": {"value": "exact_value", "unit": "mm/inch"}
                },
                "keyway_specifications": {
                    "width": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
                    "depth": {"value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"},
                    "length": {"value": "exact_value", "unit": "mm/inch"},
                    "key_standard": "DIN6885/ANSI_standard if referenced"
                },
                "geometric_tolerances": [
                    {"feature": "description", "tolerance_type": "runout/concentricity/etc", "value": "exact_value", "datum": "reference_datum"}
                ],
                "surface_specifications": {
                    "tooth_surface_finish": {"value": "Ra/Rz_value", "unit": "micrometers/microinches"},
                    "bore_surface_finish": {"value": "Ra/Rz_value", "unit": "micrometers/microinches"},
                    "material": "exact material specification",
                    "heat_treatment": "exact treatment specification",
                    "hardness": "HRC/HB value if specified"
                },
                "quality_specifications": {
                    "agma_quality_class": "if_specified",
                    "din_quality_grade": "if_specified", 
                    "inspection_requirements": ["list of special requirements"]
                },
                "manufacturing_notes": [
                    {"note": "exact_text", "location": "drawing_location", "type": "machining/assembly/inspection"}
                ],
                "section_view_data": {
                    "section_identifier": "A-A/B-B/etc",
                    "section_scale": "exact_scale",
                    "section_dimensions": [
                        {"feature": "description", "value": "exact_value", "unit": "mm/inch", "tolerance": "if_shown"}
                    ]
                },
                "specification_tables": [
                    {"table_name": "exact_name", "table_data": "structured_data_from_table"}
                ]
            }
            ```

            PRECISION REQUIREMENTS:
            - Record ALL dimension values with exact decimal precision as shown
            - Capture all tolerance notations (+0.000/-0.000, ±0.000, H7/g6, etc.)
            - Extract complete GD&T symbols with datum references
            - Note all surface finish symbols and values (32√, Ra 1.6, etc.)
            - Record material specifications exactly (AISI 4140, SAE 1045, etc.)
            - Capture heat treatment callouts precisely (58-62 HRC, through hardened, etc.)

            This is for precision gear manufacturing - extract every technical detail visible for machining and quality control.
  
            """
            
            # Count input tokens before making the request
            input_token_info = self.count_total_tokens_for_request(PROMPT, image_path)
            logger.info(f"Input tokens - Prompt: {input_token_info['prompt_tokens']}, Image: {input_token_info['image_tokens']}, Total: {input_token_info['total_input_tokens']}")
            
            uploaded_file = await self.upload_image_to_gemini(image_path)
            
            response = model.generate_content(
                [PROMPT, uploaded_file],
                generation_config={"temperature": 0.0}
            )
            response_text = response.text.strip()
            
            # Count output tokens
            output_tokens = self.count_tokens_accurate(response_text)
            total_tokens = input_token_info['total_input_tokens'] + output_tokens
            
            logger.info(f"Token usage - Input: {input_token_info['total_input_tokens']}, Output: {output_tokens}, Total: {total_tokens}")
            
            # Clean up response text
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            parsed_data = json.loads(response_text)
            logger.info("Successfully parsed JSON response from Gemini")
            
            # Add comprehensive token usage information
            parsed_data["token_usage"] = {
                "input_tokens": {
                    "prompt_tokens": input_token_info['prompt_tokens'],
                    "image_tokens": input_token_info['image_tokens'],
                    "total_input_tokens": input_token_info['total_input_tokens']
                },
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "token_counting_method": "gemini_api_with_estimation_fallback",
                "image_dimensions": self._get_image_dimensions(image_path)
            }
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            logger.error(f"Response text: {response_text[:1000]}...")
            
            # Still provide token info even on error
            input_token_info = self.count_total_tokens_for_request(PROMPT, image_path) if 'PROMPT' in locals() else {"prompt_tokens": 0, "image_tokens": 0, "total_input_tokens": 0}
            output_tokens = self.count_tokens_accurate(response_text) if 'response_text' in locals() else 0
            
            return {
                "error": f"Invalid JSON response from AI model: {str(e)}",
                "extracted_data": {},
                "token_usage": {
                    "input_tokens": input_token_info,
                    "output_tokens": output_tokens,
                    "total_tokens": input_token_info.get('total_input_tokens', 0) + output_tokens,
                    "token_counting_method": "gemini_api_with_estimation_fallback"
                }
            }
        except Exception as e:
            logger.error(f"Technical drawing extraction failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Provide token info even on error
            input_token_info = self.count_total_tokens_for_request(PROMPT, image_path) if 'PROMPT' in locals() else {"prompt_tokens": 0, "image_tokens": 0, "total_input_tokens": 0}
            
            return {
                "error": str(e),
                "file": os.path.basename(image_path),
                "token_usage": {
                    "input_tokens": input_token_info,
                    "output_tokens": 0,
                    "total_tokens": input_token_info.get('total_input_tokens', 0),
                    "token_counting_method": "gemini_api_with_estimation_fallback"
                }
            }
    
    def _get_image_dimensions(self, image_path: str) -> Dict[str, Any]:
        """Get image dimensions for token calculation reference"""
        try:
            with Image.open(image_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "total_pixels": img.width * img.height,
                    "format": img.format
                }
        except Exception:
            return {"error": "Could not read image dimensions"}

    # ... rest of your existing methods remain the same ...
    async def process_all_data(self, data: Dict, filename: str) -> List[Dict]:
        """Process all data into a flat structure for CSV output with gear-specific organization"""
        try:
            logger.info(f"Processing data for CSV output: {filename}")
            
            records = []
            
            # Create separate records for different data types
            def create_gear_records(data, filename):
                gear_records = []
                
                # Basic drawing info record
                if "drawing_info" in data:
                    drawing_record = {
                        "Filename": filename,
                        "Record_Type": "Drawing_Info",
                        **{f"Drawing_{k}": v for k, v in data["drawing_info"].items()}
                    }
                    gear_records.append(drawing_record)
                
                # Gear specifications record
                if "gear_specifications" in data:
                    gear_record = {
                        "Filename": filename,
                        "Record_Type": "Gear_Specifications",
                        **{f"Gear_{k}": v for k, v in data["gear_specifications"].items()}
                    }
                    gear_records.append(gear_record)
                
                # Dimension records (one per dimension)
                if "dimensions" in data:
                    for dim_type, dimensions in data["dimensions"].items():
                        if isinstance(dimensions, list):
                            for i, dim in enumerate(dimensions):
                                dim_record = {
                                    "Filename": filename,
                                    "Record_Type": f"Dimension_{dim_type}",
                                    "Dimension_Index": i + 1,
                                    **{f"Dim_{k}": v for k, v in dim.items()}
                                }
                                gear_records.append(dim_record)
                
                # Tolerance records
                if "tolerances_and_fits" in data and isinstance(data["tolerances_and_fits"], list):
                    for i, tol in enumerate(data["tolerances_and_fits"]):
                        tol_record = {
                            "Filename": filename,
                            "Record_Type": "Tolerance",
                            "Tolerance_Index": i + 1,
                            **{f"Tol_{k}": v for k, v in tol.items()}
                        }
                        gear_records.append(tol_record)
                
                # Material specifications
                if "material_specifications" in data:
                    material_record = {
                        "Filename": filename,
                        "Record_Type": "Material_Specifications",
                        **{f"Material_{k}": v for k, v in data["material_specifications"].items()}
                    }
                    gear_records.append(material_record)
                
                # Manufacturing notes
                if "manufacturing_notes" in data and isinstance(data["manufacturing_notes"], list):
                    for i, note in enumerate(data["manufacturing_notes"]):
                        note_record = {
                            "Filename": filename,
                            "Record_Type": "Manufacturing_Note",
                            "Note_Index": i + 1,
                            **{f"Note_{k}": v for k, v in note.items()}
                        }
                        gear_records.append(note_record)
                
                return gear_records
            
            records = create_gear_records(data, filename)
            
            # If no structured records were created, fall back to flattened approach
            if not records:
                def flatten_dict(d, parent_key='', record=None):
                    if record is None:
                        record = {"Filename": filename, "Record_Type": "General"}
                    
                    for k, v in d.items():
                        new_key = f"{parent_key}_{k}" if parent_key else k
                        
                        if isinstance(v, dict):
                            flatten_dict(v, new_key, record)
                        elif isinstance(v, list):
                            if v and isinstance(v[0], dict):
                                for i, item in enumerate(v):
                                    list_record = {"Filename": filename, "Record_Type": f"{new_key}_Item_{i+1}"}
                                    flatten_dict(item, new_key, list_record)
                                    records.append(list_record)
                            else:
                                record[new_key] = "; ".join(str(x) for x in v)
                        else:
                            record[new_key] = str(v)
                    
                    return record
                
                main_record = flatten_dict(data)
                records.append(main_record)
            
            logger.info(f"Processed {len(records)} total records")
            return records
            
        except Exception as e:
            logger.error(f"Data processing error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [{
                "Filename": filename,
                "Error": f"Data processing error: {str(e)}",
                "Record_Type": "Error"
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
                "csv_path": csv_file_path,
                "token_usage": extracted_data.get("token_usage", {})
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