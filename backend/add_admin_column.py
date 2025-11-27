#!/usr/bin/env python3
"""
Script to add is_admin column to users table.
Run this script to update the database schema.
"""
import psycopg2
import os
import sys

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://flavoruser:securepass@localhost:5432/flavorquest"
).strip()

def _build_connection_url():
    """Ensure the connection string has sslmode when required."""
    dsn = DATABASE_URL
    if "render.com" in dsn and "sslmode=" not in dsn:
        separator = "&" if "?" in dsn else "?"
        dsn = f"{dsn}{separator}sslmode=require"
    return dsn

def add_admin_column():
    """Add is_admin column to users table if it doesn't exist."""
    try:
        conn = psycopg2.connect(_build_connection_url())
        cur = conn.cursor()
        
        # Check if column already exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_admin'
        """)
        
        if cur.fetchone():
            print("Column 'is_admin' already exists in users table.")
        else:
            # Add is_admin column
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL
            """)
            conn.commit()
            print("Successfully added 'is_admin' column to users table.")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding admin column: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def set_user_as_admin(username):
    """Set a user as admin by username."""
    try:
        conn = psycopg2.connect(_build_connection_url())
        cur = conn.cursor()
        
        cur.execute("UPDATE users SET is_admin = TRUE WHERE username = %s", (username,))
        if cur.rowcount == 0:
            print(f"User '{username}' not found.")
            cur.close()
            conn.close()
            return False
        
        conn.commit()
        print(f"Successfully set user '{username}' as admin.")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting user as admin: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If username provided, set that user as admin
        username = sys.argv[1]
        if add_admin_column():
            set_user_as_admin(username)
    else:
        # Just add the column
        add_admin_column()
        print("\nTo set a user as admin, run:")
        print(f"  python {sys.argv[0]} <username>")

