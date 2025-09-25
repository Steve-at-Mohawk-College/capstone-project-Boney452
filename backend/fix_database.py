#!/usr/bin/env python3
"""
Fix database schema to match backend expectations
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def fix_database():
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname="flavorquest",
        user="flavoruser",
        password="securepass",
        host="localhost",
        port="5432"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    try:
        print("Fixing database schema...")
        
        # Drop existing restaurants table and recreate with correct schema
        cur.execute("DROP TABLE IF EXISTS restaurants CASCADE;")
        print("Dropped existing restaurants table")
        
        # Create new restaurants table with correct schema
        cur.execute("""
            CREATE TABLE restaurants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                cuisine_type VARCHAR(100),
                location TEXT,
                google_api_links TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        print("Created new restaurants table with correct schema")
        
        # Insert some sample data
        cur.execute("""
            INSERT INTO restaurants (name, cuisine_type, location, google_api_links, is_active) VALUES
            ('Sample Italian Restaurant', 'Italian', '123 Main St, New York, NY', 'https://maps.google.com/place1', TRUE),
            ('Sample Chinese Restaurant', 'Chinese', '456 Oak Ave, Los Angeles, CA', 'https://maps.google.com/place2', TRUE),
            ('Sample Mexican Restaurant', 'Mexican', '789 Pine St, Chicago, IL', 'https://maps.google.com/place3', TRUE);
        """)
        print("Inserted sample data")
        
        print("✅ Database schema fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False
    finally:
        cur.close()
        conn.close()
    
    return True

if __name__ == "__main__":
    fix_database()
