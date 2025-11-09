#!/usr/bin/env python3
"""
Weather Data Importer for RAG System

This script imports weather data from a CSV file into the Chroma DB vector store
used by the RAG agent. It converts each weather record into a searchable document
format with proper metadata.

Usage:
    python3 RAG/import_weather_data.py

Requirements:
- OpenAI API key set in environment (OPENAI_API_KEY)
- CSV file at: RAG/shared/weather_data.csv
"""

import sys
import os
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Load .env file from project root
try:
    from dotenv import load_dotenv
    # Load .env from project root (3 levels up from shared/)
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded .env from {env_path}")
except ImportError:
    pass  # dotenv not available, will use system env vars

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

class WeatherDataImporter:
    """Imports weather data CSV into RAG vector store"""
    
    def __init__(self, csv_path: str, chroma_path: str = "./.chroma", collection: str = "rag_docs"):
        self.csv_path = Path(csv_path)
        self.chroma_path = chroma_path
        self.collection = collection
        
        # Initialize vector store with same config as RAG agent
        chroma_path_str = str(chroma_path) if isinstance(chroma_path, Path) else chroma_path
        self.vector_store = VectorStore(path=chroma_path_str, collection=collection)
        
    def validate_environment(self) -> bool:
        """Check if required environment variables and files exist"""
        # Check OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY environment variable not set")
            logger.info("Set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
            return False
        
        # Check CSV file exists (convert to Path if string)
        csv_path = Path(self.csv_path) if isinstance(self.csv_path, str) else self.csv_path
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            return False
        
        logger.info("Environment validation passed")
        return True
    
    def read_weather_data(self) -> List[Dict]:
        """Read and parse the weather CSV file"""
        csv_path = Path(self.csv_path) if isinstance(self.csv_path, str) else self.csv_path
        logger.info(f"Reading weather data from: {csv_path}")
        
        weather_data = []
        try:
            with open(str(csv_path), 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row_num, row in enumerate(reader, 1):
                    weather_data.append(row)
                    
                    # Log progress for large files
                    if row_num % 10000 == 0:
                        logger.info(f"Read {row_num:,} weather records...")
            
            logger.info(f"Successfully read {len(weather_data):,} weather records")
            return weather_data
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []
    
    def create_weather_document(self, weather_record: Dict, record_id: int) -> Document:
        """Convert a weather record into a LangChain Document"""
        
        # Create a comprehensive text description of the weather data
        content = self._format_weather_content(weather_record)
        
        # Create metadata for filtering and reference
        metadata = {
            "source": "weather_data.csv",
            "type": "weather_record",
            "record_id": record_id,
            "location": weather_record.get("Location", ""),
            "date_time": weather_record.get("Date_Time", ""),
            "temperature_c": float(weather_record.get("Temperature_C", 0)),
            "humidity_pct": float(weather_record.get("Humidity_pct", 0)),
            "precipitation_mm": float(weather_record.get("Precipitation_mm", 0)),
            "wind_speed_kmh": float(weather_record.get("Wind_Speed_kmh", 0))
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _format_weather_content(self, record: Dict) -> str:
        """Format weather record into natural language for better semantic search"""
        
        location = record.get("Location", "Unknown location")
        date_time = record.get("Date_Time", "Unknown time")
        temp_c = float(record.get("Temperature_C", 0))
        humidity = float(record.get("Humidity_pct", 0))
        precipitation = float(record.get("Precipitation_mm", 0))
        wind_speed = float(record.get("Wind_Speed_kmh", 0))
        
        # Convert temperature to Fahrenheit for additional searchability
        temp_f = (temp_c * 9/5) + 32
        
        # Create natural language description
        content = f"""Weather Report for {location}
Recorded on: {date_time}

Temperature: {temp_c:.1f}°C ({temp_f:.1f}°F)
Humidity: {humidity:.1f}%
Precipitation: {precipitation:.2f}mm
Wind Speed: {wind_speed:.1f} km/h

Weather Conditions:
- Location: {location} area weather conditions
- Date and Time: {date_time}
- Temperature reading of {temp_c:.1f} degrees Celsius
- Relative humidity at {humidity:.1f} percent
- Precipitation measurement of {precipitation:.2f} millimeters
- Wind speed recorded at {wind_speed:.1f} kilometers per hour

Weather Summary: On {date_time}, {location} experienced temperatures of {temp_c:.1f}°C with {humidity:.1f}% humidity. """
        
        # Add weather condition descriptions for better semantic search
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
        
        if wind_speed > 20:
            content += "It was windy with strong winds."
        elif wind_speed > 10:
            content += "There was a moderate breeze."
        else:
            content += "The air was calm with light winds."
        
        return content
    
    def import_to_vector_store(self, weather_data: List[Dict]) -> bool:
        """Import weather data into the vector store"""
        logger.info(f"Converting {len(weather_data):,} weather records to documents...")
        
        try:
            # Convert weather records to Document objects
            documents = []
            for i, record in enumerate(weather_data):
                doc = self.create_weather_document(record, i + 1)
                documents.append(doc)
                
                # Log progress for large datasets
                if (i + 1) % 5000 == 0:
                    logger.info(f"Converted {i + 1:,} records to documents...")
            
            logger.info(f"Created {len(documents):,} documents")
            
            # Check if vector store already exists and load it
            try:
                logger.info("Checking for existing vector store...")
                self.vector_store.load()
                logger.info("Loaded existing vector store")
                
                # Add new documents to existing store
                logger.info("Adding weather documents to existing vector store...")
                self.vector_store.vs.add_documents(documents)
                
            except Exception as e:
                logger.info("Creating new vector store with weather data...")
                # Create new vector store from documents
                from langchain_chroma import Chroma
                self.vector_store.vs = Chroma.from_documents(
                    documents, 
                    self.vector_store.emb, 
                    collection_name=self.vector_store.collection, 
                    persist_directory=self.vector_store.path
                )
            
            # Persist the vector store (Chroma auto-persists when persist_directory is set)
            logger.info("Persisting vector store to disk...")
            try:
                if hasattr(self.vector_store.vs, 'persist'):
                    self.vector_store.vs.persist()
            except AttributeError:
                # Newer Chroma versions auto-persist, no need to call persist()
                pass
            
            logger.info("Weather data successfully imported to vector store!")
            return True
            
        except Exception as e:
            logger.error(f"Error importing to vector store: {e}")
            return False
    
    def test_search(self) -> bool:
        """Test the imported data with sample searches"""
        logger.info("Testing weather data search functionality...")
        
        try:
            # Load the vector store
            self.vector_store.load()
            
            test_queries = [
                "weather in New York",
                "hot temperatures above 30 degrees",
                "rainy weather with precipitation",
                "windy conditions",
                "cold weather below freezing"
            ]
            
            for query in test_queries:
                logger.info(f"Testing query: '{query}'")
                results = self.vector_store.search(query, k=3)
                
                if results:
                    logger.info(f"Found {len(results)} results")
                    for i, result in enumerate(results, 1):
                        location = result.metadata.get('location', 'Unknown')
                        date_time = result.metadata.get('date_time', 'Unknown')
                        temp = result.metadata.get('temperature_c', 'N/A')
                        logger.info(f"   {i}. {location} on {date_time} - {temp}°C")
                else:
                    logger.warning(f"No results found for: '{query}'")
                
                logger.info("")
            
            logger.info("Search testing completed!")
            return True
            
        except Exception as e:
            logger.error(f"Error testing search: {e}")
            return False

def main():
    """Main function to run the weather data import"""
    logger.info("Weather Data Importer for RAG System")
    logger.info("=" * 50)
    
    # Configuration
    # Get paths relative to script location
    script_dir = Path(__file__).parent
    csv_path = script_dir / "weather_data.csv"
    # Vector store should be in RAG directory, not shared
    rag_dir = script_dir.parent
    chroma_path = rag_dir / ".chroma"
    collection = "rag_docs"    # Same collection as RAG agent
    
    # Initialize importer
    importer = WeatherDataImporter(csv_path, chroma_path, collection)
    
    # Validate environment
    if not importer.validate_environment():
        logger.error("Environment validation failed. Please fix the issues above.")
        return False
    
    # Read weather data
    weather_data = importer.read_weather_data()
    if not weather_data:
        logger.error("Failed to read weather data")
        return False
    
    # Import to vector store
    success = importer.import_to_vector_store(weather_data)
    if not success:
        logger.error("Failed to import weather data")
        return False
    
    # Test the imported data
    importer.test_search()
    
    logger.info("Import completed successfully!")
    logger.info(f"Imported {len(weather_data):,} weather records")
    logger.info(f"Data stored in: {chroma_path}/{collection}")
    logger.info("\nYou can now query weather data through the RAG agent!")
    logger.info("Example queries:")
    logger.info('  - "What was the weather like in New York?"')
    logger.info('  - "Show me hot weather data above 30 degrees"')
    logger.info('  - "Find rainy days with high precipitation"')
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
