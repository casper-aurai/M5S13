#!/usr/bin/env python3
import requests
import json

def seed_weaviate():
    # Weaviate endpoint
    weaviate_url = "http://localhost:8081"
    
    # Sample documents to embed
    documents = [
        {
            "content": "This is a sample document about data modeling and database design patterns.",
            "metadata": {"source": "sample1", "type": "documentation"}
        },
        {
            "content": "Graph databases are excellent for modeling complex relationships between entities.",
            "metadata": {"source": "sample2", "type": "tutorial"}
        }
    ]
    
    # Create a class for documents
    schema = {
        "class": "Document",
        "description": "A document with vector embeddings",
        "properties": [
            {
                "name": "content",
                "dataType": ["text"],
                "description": "The content of the document"
            },
            {
                "name": "metadata",
                "dataType": ["object"],
                "description": "Metadata about the document",
                "nestedProperties": [
                    {"name": "source", "dataType": ["string"]},
                    {"name": "type", "dataType": ["string"]}
                ]
            }
        ]
    }
    
    # Create the class
    response = requests.post(
        f"{weaviate_url}/v1/schema",
        headers={"Content-Type": "application/json"},
        json=schema
    )
    
    if response.status_code not in [200, 201]:
        print(f"Failed to create schema: {response.text}")
        return
    
    print("Schema created successfully")
    
    # Add documents (without vectors for now - would need an embedding model)
    for i, doc in enumerate(documents):
        data_object = {
            "content": doc["content"],
            "metadata": doc["metadata"]
        }
        
        response = requests.post(
            f"{weaviate_url}/v1/objects",
            headers={"Content-Type": "application/json"},
            json=data_object
        )
        
        if response.status_code in [200, 201]:
            print(f"Added document {i+1}")
        else:
            print(f"Failed to add document {i+1}: {response.text}")
    
    print("Weaviate seeding completed")

if __name__ == "__main__":
    seed_weaviate()
