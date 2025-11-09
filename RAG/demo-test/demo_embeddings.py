#!/usr/bin/env python3
"""
Vector Embeddings Demo - Shows how weather data gets processed

This demonstrates the embedding process without using the OpenAI API.
Shows exactly what happens when converting weather data to vector embeddings.
"""

import csv
import json
from typing import Dict

def create_weather_document_demo(weather_record: Dict, record_id: int) -> Dict:
    """Demo: Convert a weather record into a document (like what gets embedded)"""
    
    location = weather_record.get("Location", "Unknown location")
    date_time = weather_record.get("Date_Time", "Unknown time")
    temp_c = float(weather_record.get("Temperature_C", 0))
    humidity = float(weather_record.get("Humidity_pct", 0))
    precipitation = float(weather_record.get("Precipitation_mm", 0))
    wind_speed = float(weather_record.get("Wind_Speed_kmh", 0))
    
    # Convert temperature to Fahrenheit
    temp_f = (temp_c * 9/5) + 32
    
    # Create natural language description (this is what gets embedded)
    content = f"""Weather Report for {location}
Recorded on: {date_time}

Temperature: {temp_c:.1f}°C ({temp_f:.1f}°F)
Humidity: {humidity:.1f}%
Precipitation: {precipitation:.2f}mm
Wind Speed: {wind_speed:.1f} km/h

Weather Conditions in {location}: On {date_time}, the temperature was {temp_c:.1f} degrees Celsius with {humidity:.1f}% humidity. """
    
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
    
    # Create metadata (stored alongside the vector)
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
    
    return {
        "content": content,
        "metadata": metadata,
        "embedding_note": "This text would be converted to 1536-dimensional vector using OpenAI text-embedding-3-small"
    }

def demo_search_scenarios():
    """Show what types of searches would work with the embeddings"""
    
    search_scenarios = [
        {
            "user_query": "What was the weather like in New York during winter?",
            "how_it_works": "Vector similarity finds documents with 'New York' + cold temperatures + winter dates",
            "semantic_matches": ["freezing temperatures", "very cold", "winter months", "New York"]
        },
        {
            "user_query": "Show me hot weather above 30 degrees",
            "how_it_works": "Finds vectors with high temperature values and 'hot' descriptions",
            "semantic_matches": ["hot weather", "warm temperatures", "above 30", "pleasant weather"]
        },
        {
            "user_query": "Find rainy days with heavy precipitation", 
            "how_it_works": "Matches precipitation-related text and high mm values",
            "semantic_matches": ["heavy precipitation", "rain", "wet weather", "storm"]
        },
        {
            "user_query": "Humid weather in tropical cities",
            "how_it_works": "Combines humidity descriptions with location patterns",
            "semantic_matches": ["very humid", "tropical", "moisture", "sticky weather"]
        }
    ]
    
    return search_scenarios

def main():
    """Demo the embedding process"""
    print(" Vector Embeddings Demo for Weather Data")
    print("=" * 50)
    
    # Read a few sample records
    csv_path = "weather_data.csv"
    try:
        with open(csv_path, 'r') as file:
            reader = csv.DictReader(file)
            sample_records = [next(reader) for _ in range(3)]
    except:
        print(" Could not read weather_data.csv")
        return
    
    print(f" Processing {len(sample_records)} sample weather records...\n")
    
    # Show how records get converted to embeddable documents
    for i, record in enumerate(sample_records, 1):
        print(f"  SAMPLE RECORD #{i}")
        print("-" * 30)
        
        # Show raw CSV data
        print(" Raw CSV Data:")
        for key, value in record.items():
            print(f"  {key}: {value}")
        
        # Show converted document
        document = create_weather_document_demo(record, i)
        print(f"\n Natural Language Document (gets embedded):")
        print(f"\"\"\"")
        print(document["content"])
        print(f"\"\"\"")
        
        print(f"\n  Metadata (stored with vector):")
        print(json.dumps(document["metadata"], indent=2))
        
        print(f"\n {document['embedding_note']}")
        print("\n" + "="*60 + "\n")
    
    # Show search scenarios
    print(" SEMANTIC SEARCH CAPABILITIES")
    print("=" * 50)
    
    scenarios = demo_search_scenarios()
    for i, scenario in enumerate(scenarios, 1):
        print(f" Search Scenario #{i}")
        print(f"User Query: \"{scenario['user_query']}\"")
        print(f"How it works: {scenario['how_it_works']}")
        print(f"Semantic matches: {', '.join(scenario['semantic_matches'])}")
        print()
    
    print(" EMBEDDING PROCESS SUMMARY")
    print("=" * 50)
    print("1.  Raw weather data → Natural language descriptions")
    print("2.  OpenAI text-embedding-3-small → 1536-dimensional vectors")
    print("3.  Chroma DB → Stores vectors + metadata for fast similarity search")
    print("4.  User queries → Vector similarity → Relevant weather records")
    print("5.  RAG Agent → Generates natural language responses")
    
    print(f"\n SCALE:")
    print(f"• Your CSV: 1,000,000 weather records")
    print(f"• Embeddings: 1,000,000 vectors (1536 dimensions each)")
    print(f"• Storage: ~6GB of vector data in Chroma DB")
    print(f"• Search: Sub-second semantic similarity queries")
    
    print(f"\n NEXT STEPS:")
    print(f"• Wait for OpenAI quota to reset (24 hours)")
    print(f"• Or upgrade OpenAI plan for higher limits")
    print(f"• Run import script when quota available")
    print(f"• Test weather queries through RAG agent")

if __name__ == "__main__":
    main()
