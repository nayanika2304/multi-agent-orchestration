#!/usr/bin/env python3
"""
Weather Data Sample Importer for RAG System

Imports a smaller sample of weather data to work within API quotas.
This version imports only the first 1000 records for testing.
"""

import sys
import os
import csv
import logging
from pathlib import Path
from typing import List, Dict

# Add the RAG directory to Python path for shared modules  
current_dir = Path(__file__).parent
rag_dir = current_dir.parent
sys.path.insert(0, str(rag_dir))

# Import vectorstore from the same directory since we're in shared/
from vectorstore import VectorStore
from langchain_core.documents import Document

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_weather_document(weather_record: Dict, record_id: int) -> Document:
    """Convert a weather record into a LangChain Document"""
    
    location = weather_record.get("Location", "Unknown location")
    date_time = weather_record.get("Date_Time", "Unknown time")
    temp_c = float(weather_record.get("Temperature_C", 0))
    humidity = float(weather_record.get("Humidity_pct", 0))
    precipitation = float(weather_record.get("Precipitation_mm", 0))
    wind_speed = float(weather_record.get("Wind_Speed_kmh", 0))
    
    # Convert temperature to Fahrenheit for additional searchability
    temp_f = (temp_c * 9/5) + 32
    
    # Create natural language description
    content = f"""Weather Report for {location}
Recorded on: {date_time}

Temperature: {temp_c:.1f}°C ({temp_f:.1f}°F)
Humidity: {humidity:.1f}%
Precipitation: {precipitation:.2f}mm
Wind Speed: {wind_speed:.1f} km/h

Weather Conditions in {location}: On {date_time}, the temperature was {temp_c:.1f} degrees Celsius with {humidity:.1f}% humidity. """
    
    # Add weather condition descriptions
    if temp_c < 0:
        content += "The weather was very cold with freezing temperatures. "
    elif temp_c < 10:
        content += "The weather was cold. "
    elif temp_c < 20:
        content += "The weather was cool and mild. "
    elif temp_c < 30:
        content += "The weather was warm and pleasant. "
    else:
        content += "The weather was hot. "
    
    if humidity > 80:
        content += "It was very humid. "
    elif humidity > 60:
        content += "It was moderately humid. "
    else:
        content += "It was relatively dry. "
    
    if precipitation > 10:
        content += "There was heavy precipitation or rain. "
    elif precipitation > 1:
        content += "There was light to moderate precipitation. "
    elif precipitation > 0:
        content += "There was minimal precipitation. "
    else:
        content += "There was no precipitation. "
    
    # Create metadata
    metadata = {
        "source": "weather_data.csv",
        "type": "weather_record",
        "record_id": record_id,
        "location": location,
        "date_time": date_time,
        "temperature_c": temp_c,
        "humidity_pct": humidity,
        "precipitation_mm": precipitation,
        "wind_speed_kmh": wind_speed
    }
    
    return Document(page_content=content, metadata=metadata)

def main():
    """Import a sample of weather data"""
    logger.info("🌤️  Weather Data Sample Importer for RAG System")
    logger.info("=" * 50)
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY environment variable not set")
        return False
    
    # Configuration
    csv_path = "../shared/weather_data.csv"
    sample_size = 1000  # Only import first 1000 records
    chroma_path = "./.chroma"
    collection = "rag_docs"
    
    logger.info(f"📝 Importing {sample_size} weather records (sample)")
    
    # Read sample data
    weather_data = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                if i >= sample_size:
                    break
                weather_data.append(row)
    except Exception as e:
        logger.error(f"❌ Error reading CSV: {e}")
        return False
    
    logger.info(f"✅ Read {len(weather_data)} weather records")
    
    # Convert to documents
    documents = []
    for i, record in enumerate(weather_data):
        doc = create_weather_document(record, i + 1)
        documents.append(doc)
    
    logger.info(f"✅ Created {len(documents)} documents")
    
    # Import to vector store
    try:
        vector_store = VectorStore(path=chroma_path, collection=collection)
        
        # Try to load existing store
        try:
            vector_store.load()
            logger.info("✅ Loaded existing vector store")
            vector_store.vs.add_documents(documents)
            logger.info("➕ Added weather documents to existing store")
        except:
            logger.info("📦 Creating new vector store")
            from langchain_chroma import Chroma
            vector_store.vs = Chroma.from_documents(
                documents, 
                vector_store.emb, 
                collection_name=collection, 
                persist_directory=chroma_path
            )
        
        # Persist
        vector_store.vs.persist()
        logger.info("💾 Vector store persisted")
        
        # Test search
        logger.info("🧪 Testing search...")
        results = vector_store.search("weather in New York", k=3)
        if results:
            logger.info(f"✅ Search test passed - found {len(results)} results")
            for i, result in enumerate(results, 1):
                location = result.metadata.get('location', 'Unknown')
                temp = result.metadata.get('temperature_c', 'N/A')
                logger.info(f"   {i}. {location} - {temp}°C")
        
        logger.info("🎉 Sample weather data import completed!")
        logger.info(f"📊 Imported {len(documents)} weather records")
        logger.info("💡 You can now query weather data through the RAG agent!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error importing to vector store: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
