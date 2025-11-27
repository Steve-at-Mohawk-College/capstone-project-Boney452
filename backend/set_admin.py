#!/usr/bin/env python3
"""
Script to set a user as admin.
Usage: python set_admin.py <username>
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

def ensure_admin_column():
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
        
        # First check if user exists
        cur.execute("SELECT id, username, email, is_admin FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if not user:
            print(f"❌ User '{username}' not found in database.")
            print(f"\nPlease create the user first by:")
            print(f"  1. Signing up through the application, OR")
            print(f"  2. Creating the user manually in the database")
            cur.close()
            conn.close()
            return False
        
        # Check if already admin
        if user[3]:  # is_admin column
            print(f"✅ User '{username}' is already an admin.")
            cur.close()
            conn.close()
            return True
        
        # Set user as admin
        cur.execute("UPDATE users SET is_admin = TRUE WHERE username = %s", (username,))
        conn.commit()
        
        print(f"✅ Successfully set user '{username}' (ID: {user[0]}, Email: {user[2]}) as admin.")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error setting user as admin: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_admin.py <username>")
        print("\nExample:")
        print("  python set_admin.py admin123")
        sys.exit(1)
    
    username = sys.argv[1]
    
    print(f"Setting up admin for user: {username}")
    print("-" * 50)
    
    # Ensure admin column exists
    if not ensure_admin_column():
        print("Failed to ensure admin column exists. Exiting.")
        sys.exit(1)
    
    # Set user as admin
    if set_user_as_admin(username):
        print("-" * 50)
        print(f"✅ Admin setup complete for '{username}'!")
        print("\nThe user can now:")
        print("  - See all groups in the chat system")
        print("  - Delete any group")
        print("  - Delete any review/rating")
        print("  - Delete any message")
    else:
        sys.exit(1)

