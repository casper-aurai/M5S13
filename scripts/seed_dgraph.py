#!/usr/bin/env python3
"""
Seed script for Dgraph.

Seeds Dgraph with initial schema and sample data for testing.
"""

import os
import sys

try:
    from pydgraph import DgraphClient, DgraphClientStub
except ImportError:
    print("pydgraph not installed. Install with: pip install pydgraph")
    sys.exit(1)

def seed_dgraph():
    """Seed Dgraph with schema and sample data."""
    dgraph_host = os.getenv('DGRAPH_HOST', 'localhost:9080')

    try:
        stub = DgraphClientStub(dgraph_host)
        client = DgraphClient(stub)

        # Drop all data (for testing)
        client.alter({"drop_all": True})

        # Define schema
        schema = """
            name: string @index(exact) .
            files: [uid] @reverse .
            path: string @index(exact) .
            language: string @index(exact) .
            functions: [string] .
            classes: [string] .
            imports: [string] .
            tables: [string] .
            complexity: string .
        """

        client.alter(schema)

        # Add sample data
        mutations = [
            {
                "name": "demo-repo",
                "files": [
                    {
                        "path": "/demo/models/user.py",
                        "language": "python",
                        "functions": ["create_user", "authenticate"],
                        "classes": ["User", "AuthService"],
                        "imports": ["flask", "sqlalchemy"],
                        "complexity": "medium"
                    },
                    {
                        "path": "/demo/models/orders.sql",
                        "language": "sql",
                        "tables": ["users", "orders", "products"],
                        "complexity": "low"
                    }
                ]
            }
        ]

        client.txn().mutate(set_obj=mutations)
        client.txn().commit()

        print("✅ Dgraph seeded successfully with sample data")

    except Exception as e:
        print(f"❌ Error seeding Dgraph: {e}")
        sys.exit(1)
    finally:
        stub.close()

if __name__ == "__main__":
    seed_dgraph()
