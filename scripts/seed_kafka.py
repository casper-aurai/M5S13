#!/usr/bin/env python3
"""
Seed script for Kafka.

Seeds Kafka topics with sample messages for testing the pipeline.
"""

import json
import os
import sys
import time

try:
    from kafka import KafkaProducer
except ImportError:
    print("kafka-python not installed. Install with: pip install kafka-python")
    sys.exit(1)

def seed_kafka():
    """Seed Kafka topics with sample data."""
    kafka_brokers = os.getenv('KAFKA_BROKERS', 'localhost:9092')

    try:
        producer = KafkaProducer(
            bootstrap_servers=[kafka_brokers],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )

        # Sample ingestion message
        ingestion_message = {
            "repo": "demo-repo",
            "ref": "main",
            "path": "/demo",
            "ts": time.time()
        }

        # Sample mined file messages
        mined_messages = [
            {
                "repo": "demo-repo",
                "file": "/demo/models/user.py",
                "lang": "python",
                "size": 1234,
                "hash": "sha256-demo123",
                "ts": time.time()
            },
            {
                "repo": "demo-repo",
                "file": "/demo/models/orders.sql",
                "lang": "sql",
                "size": 567,
                "hash": "sha256-demo456",
                "ts": time.time()
            }
        ]

        # Sample analyzed messages
        analyzed_messages = [
            {
                "repo": "demo-repo",
                "file": "/demo/models/user.py",
                "lang": "python",
                "findings": {
                    "functions": ["create_user", "authenticate"],
                    "classes": ["User", "AuthService"],
                    "imports": ["flask", "sqlalchemy"],
                    "complexity": "medium"
                },
                "ts": time.time()
            },
            {
                "repo": "demo-repo",
                "file": "/demo/models/orders.sql",
                "lang": "sql",
                "findings": {
                    "tables": ["users", "orders", "products"],
                    "complexity": "low"
                },
                "ts": time.time()
            }
        ]

        # Send messages
        future = producer.send('repos.ingested', value=ingestion_message)
        future.get(timeout=10)
        print("✅ Sent sample message to repos.ingested")

        for msg in mined_messages:
            future = producer.send('code.mined', value=msg)
            future.get(timeout=10)
        print(f"✅ Sent {len(mined_messages)} sample messages to code.mined")

        for msg in analyzed_messages:
            future = producer.send('code.analyzed', value=msg)
            future.get(timeout=10)
        print(f"✅ Sent {len(analyzed_messages)} sample messages to code.analyzed")

        producer.flush()
        producer.close()

        print("✅ Kafka seeded successfully with sample data")

    except Exception as e:
        print(f"❌ Error seeding Kafka: {e}")
        sys.exit(1)

if __name__ == "__main__":
    seed_kafka()
