import fitz  # PyMuPDF
from PIL import Image
import io
import torch
from sentence_transformers import SentenceTransformer
from torchvision import transforms
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from langchain.text_splitter import RecursiveCharacterTextSplitter
from collections import defaultdict
import numpy as np
import time
from tqdm import tqdm

# Configuration
PDF_PATH = "Test.pdf"  # Replace with your PDF path
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "newdrawingDemo"
BATCH_SIZE = 200  # Increased for faster execution
CHUNK_SIZE = 512
CHUNK_OVERLAP = 80
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

def connect_to_milvus():
    """Connect to Milvus and create collection if it doesn't exist. Auto-drop and recreate if schema is wrong."""
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    expected_fields = {"id", "embedding", "page_num", "content_type", "group_id", "chunk_text", "chunk_index", "metadata", "source_file"}
    recreate = False
    if utility.has_collection(COLLECTION_NAME):
        collection = Collection(COLLECTION_NAME)
        schema_fields = set(f.name for f in collection.schema.fields)
        if schema_fields != expected_fields:
            print(f"Schema mismatch detected. Dropping and recreating collection '{COLLECTION_NAME}'...")
            utility.drop_collection(COLLECTION_NAME)
            recreate = True
    else:
        recreate = True
    if recreate:
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
            FieldSchema(name="page_num", dtype=DataType.INT64),
            FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=10),
            FieldSchema(name="group_id", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=255)
        ]
        schema = CollectionSchema(fields, "PDF embeddings with text chunks")
        collection = Collection(COLLECTION_NAME, schema)
        collection.create_index(field_name="embedding", index_params={
            "index_type": "IVF_FLAT", 
            "metric_type": "L2", 
            "params": {"nlist": 256}  # Increased for better performance
        })
    collection.load()
    return collection

def extract_pdf_content_optimized(pdf_path):
    """Extract text and images from PDF with optimized processing."""
    doc = fitz.open(pdf_path)
    text_entities = []
    image_entities = []

    print(f"Processing {len(doc)} pages...")
    
    for page_num in tqdm(range(len(doc)), desc="Extracting content"):
        page = doc.load_page(page_num)
        
        # Extract all text from page at once (more efficient)
        page_text = page.get_text()
        if page_text.strip():
            text_entities.append({
                "page_num": page_num + 1,
                "content_type": "text",
                "data": page_text.strip(),
                "group_id": f"page_{page_num + 1}"
            })

        # Extract images (only if needed - you can disable this for faster processing)
        image_list = page.get_images(full=True)
        for img_idx, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_entities.append({
                    "page_num": page_num + 1,
                    "content_type": "image",
                    "data": image_bytes,
                    "group_id": f"page_{page_num + 1}_img_{img_idx}"
                })
            except Exception as e:
                print(f"Error extracting image on page {page_num + 1}: {e}")
                continue

    doc.close()
    return text_entities, image_entities

def create_text_chunks(text_entities):
    """Split text entities into chunks using RecursiveCharacterTextSplitter."""
    chunks = []
    
    print("Creating text chunks...")
    for entity in tqdm(text_entities, desc="Chunking text"):
        text_chunks = text_splitter.split_text(entity["data"])
        
        for chunk_idx, chunk in enumerate(text_chunks):
            chunks.append({
                "page_num": entity["page_num"],
                "content_type": "text",
                "data": chunk,
                "group_id": f"{entity['group_id']}_chunk_{chunk_idx}",
                "chunk_index": chunk_idx
            })
    
    return chunks

def load_models():
    """Load and cache models for reuse."""
    print("Loading models...")
    text_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2', device=DEVICE)
    
    # Load DINO model (only if processing images)
    try:
        image_model = torch.hub.load('facebookresearch/dino:main', 'dino_vitb16', pretrained=True)
        image_model.eval()
        image_model.to(DEVICE)
    except Exception as e:
        print(f"Warning: Could not load DINO model: {e}")
        image_model = None
    
    return text_model, image_model

def generate_embeddings_batch(entities, text_model, image_model=None):
    """Generate embeddings in batches for better performance."""
    embeddings = []
    
    # Separate text and image entities
    text_entities = [e for e in entities if e["content_type"] == "text"]
    image_entities = [e for e in entities if e["content_type"] == "image"]
    
    # Process text entities in batches
    if text_entities:
        print(f"Processing {len(text_entities)} text chunks...")
        text_data = [entity["data"] for entity in text_entities]
        
        # Process in batches to avoid memory issues
        text_batch_size = 64  # Adjust based on GPU memory
        for i in tqdm(range(0, len(text_data), text_batch_size), desc="Text embeddings"):
            batch_texts = text_data[i:i + text_batch_size]
            batch_entities = text_entities[i:i + text_batch_size]
            
            # Generate embeddings for batch
            batch_embeddings = text_model.encode(
                batch_texts, 
                convert_to_numpy=True, 
                show_progress_bar=False,
                batch_size=32  # Internal batch size for sentence-transformers
            )
            
            # Normalize and store
            for j, embedding in enumerate(batch_embeddings):
                entity = batch_entities[j]
                normalized_embedding = embedding / np.linalg.norm(embedding)
                
                embeddings.append({
                    "embedding": normalized_embedding.tolist(),
                    "page_num": entity["page_num"],
                    "content_type": entity["content_type"],
                    "group_id": entity["group_id"],
                    "chunk_text": entity["data"],
                    "chunk_index": entity.get("chunk_index", 0),
                    "metadata": f"Page {entity['page_num']} - {entity['data'][:100]}..."
                })
    
    # Process image entities (if image model is available)
    if image_entities and image_model:
        print(f"Processing {len(image_entities)} images...")
        preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        for entity in tqdm(image_entities, desc="Image embeddings"):
            try:
                image = Image.open(io.BytesIO(entity["data"])).convert('RGB')
                image_tensor = preprocess(image).unsqueeze(0).to(DEVICE)
                
                with torch.no_grad():
                    embedding = image_model(image_tensor).cpu().numpy().flatten()
                    normalized_embedding = embedding / np.linalg.norm(embedding)
                
                embeddings.append({
                    "embedding": normalized_embedding.tolist(),
                    "page_num": entity["page_num"],
                    "content_type": entity["content_type"],
                    "group_id": entity["group_id"],
                    "chunk_text": f"Image from page {entity['page_num']}",
                    "chunk_index": 0,
                    "metadata": f"Image from page {entity['page_num']}"
                })
            except Exception as e:
                print(f"Error processing image: {e}")
                continue
    
    return embeddings

def insert_to_milvus_optimized(collection, embeddings):
    """Insert embeddings into Milvus with optimized batch processing."""
    num_images = sum(1 for e in embeddings if e["content_type"] == "image")
    num_texts = sum(1 for e in embeddings if e["content_type"] == "text")
    print(f"Inserting {len(embeddings)} embeddings into Milvus... ({num_texts} text, {num_images} image)")
    total_inserted = 0
    for i in tqdm(range(0, len(embeddings), BATCH_SIZE), desc="Inserting to Milvus"):
        batch = embeddings[i:i + BATCH_SIZE]
        try:
            data = [
                [e["embedding"] for e in batch],
                [e["page_num"] for e in batch],
                [e["content_type"] for e in batch],
                [e["group_id"] for e in batch],
                [e["chunk_text"] for e in batch],
                [e["chunk_index"] for e in batch],
                [e["metadata"] for e in batch],
                [e.get("source_file", PDF_PATH) for e in batch]
            ]
            collection.insert(data)
            total_inserted += len(batch)
        except Exception as e:
            print(f"Error inserting batch: {e}")
            continue
    collection.flush()
    print(f"Successfully inserted {total_inserted} entities.")

def query_milvus_enhanced(collection, query_text, limit=10, only_images=False):
    """Enhanced query function with better results display. Set only_images=True to print only image results."""
    text_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2', device=DEVICE)
    start_time = time.time()
    query_embedding = text_model.encode([query_text], convert_to_numpy=True, show_progress_bar=False)[0]
    query_embedding = query_embedding / np.linalg.norm(query_embedding)
    search_params = {"metric_type": "L2", "params": {"nprobe": 32}}
    output_fields = ["page_num", "content_type", "group_id", "chunk_text", "chunk_index", "metadata"]
    results = collection.search(
        data=[query_embedding.tolist()],
        anns_field="embedding",
        param=search_params,
        limit=limit*5 if only_images else limit,
        output_fields=output_fields
    )
    query_time = time.time() - start_time
    if only_images:
        print(f"\n=== Image Embedding Query Results (Time: {query_time:.3f}s) ===")
    else:
        print(f"\n=== Query Results (Time: {query_time:.3f}s) ===")
    print(f"Query: '{query_text}'\n")
    num_images = 0
    num_texts = 0
    count = 0
    for i, hit in enumerate(results[0], 1):
        ctype = hit.entity.get('content_type')
        if only_images and ctype != 'image':
            continue
        if ctype == 'image':
            num_images += 1
        elif ctype == 'text':
            num_texts += 1
        if only_images and num_images > limit:
            break
        count += 1
        print(f"{count}. Page {hit.entity.get('page_num')} | Type: {ctype}")
        print(f"   Score: {hit.distance:.4f}")
        print(f"   Content: {hit.entity.get('chunk_text', 'N/A')}")
        if ctype == 'text' and hit.entity.get('chunk_index', 0) > 0:
            print(f"   Chunk Index: {hit.entity.get('chunk_index')}")
        print(f"   Group: {hit.entity.get('group_id')}")
        print()
    if only_images:
        print(f"Total image results: {num_images}")
        if num_images == 0:
            print("No image embeddings found for this query.")
    else:
        print(f"Total text results: {num_texts}, Total image results: {num_images}")

def query_only_images(collection, limit=10):
    """Query and print only image embeddings from Milvus."""
    search_params = {"metric_type": "L2", "params": {"nprobe": 32}}
    output_fields = ["page_num", "content_type", "group_id", "chunk_text", "chunk_index", "metadata"]
    # Dummy embedding for search (returns closest, but we filter for images)
    dummy_embedding = np.zeros(768, dtype=np.float32).tolist()
    results = collection.search(
        data=[dummy_embedding],
        anns_field="embedding",
        param=search_params,
        limit=limit*2,  # get more, filter below
        output_fields=output_fields
    )
    print(f"\n=== Image Embedding Results ===")
    count = 0
    for i, hit in enumerate(results[0], 1):
        if hit.entity.get('content_type') == 'image':
            count += 1
            print(f"{count}. Page {hit.entity.get('page_num')} | Type: image")
            print(f"   Score: {hit.distance:.4f}")
            print(f"   Content: {hit.entity.get('chunk_text', 'N/A')}")
            print(f"   Group: {hit.entity.get('group_id')}")
            print()
        if count >= limit:
            break
    if count == 0:
        print("No image embeddings found.")

def main():
    """Optimized main function."""
    start_time = time.time()
    # Connect to Milvus
    collection = connect_to_milvus()
    # Check if embeddings for this PDF already exist
    expr = f"source_file == '{PDF_PATH}'"
    try:
        existing = collection.query(expr, output_fields=["id"])
    except Exception as e:
        existing = []
    if existing and len(existing) > 0:
        print(f"Embeddings for '{PDF_PATH}' already exist in Milvus. Skipping embedding step.")
    else:
        # Extract content
        text_entities, image_entities = extract_pdf_content_optimized(PDF_PATH)
        # Create text chunks
        text_chunks = create_text_chunks(text_entities)
        # Combine all entities
        all_entities = text_chunks + image_entities
        print(f"Total entities to process: {len(all_entities)}")
        # Load models
        text_model, image_model = load_models()
        # Add source_file field to each entity
        for e in all_entities:
            e["source_file"] = PDF_PATH
        embeddings = generate_embeddings_batch(all_entities, text_model, image_model)
        # Insert to Milvus
        insert_to_milvus_optimized(collection, embeddings)
        total_time = time.time() - start_time
        print(f"\n=== Processing Complete ===")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Processed {len(embeddings)} chunks")
        print(f"Average time per chunk: {total_time/len(embeddings):.3f} seconds")
    # Example queries
    query_text = "Possible Contents of a 3D Data Set"
    query_milvus_enhanced(collection, query_text, limit=5)
    # Query only image embeddings for the same query
    query_milvus_enhanced(collection, query_text, limit=5, only_images=True)

if __name__ == "__main__":
    main()