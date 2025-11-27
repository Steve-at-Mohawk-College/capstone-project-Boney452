#!/usr/bin/env python3
"""
Script to create a new admin user.
Usage: python create_admin_user.py <username> <email> <password>
"""
import psycopg2
import os
import sys
from argon2 import PasswordHasher

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
            print("Column 'is_admin' already exists.")
        else:
            # Add is_admin column
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL
            """)
            conn.commit()
            print("✅ Added 'is_admin' column to users table.")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error adding admin column: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def create_admin_user(username, email, password):
    """Create a new admin user."""
    try:
        conn = psycopg2.connect(_build_connection_url())
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT id, username, email FROM users WHERE username = %s OR email = %s", (username, email))
        existing = cur.fetchone()
        
        if existing:
            print(f"⚠️  User already exists:")
            print(f"   ID: {existing[0]}")
            print(f"   Username: {existing[1]}")
            print(f"   Email: {existing[2]}")
            
            # Check if already admin
            cur.execute("SELECT is_admin FROM users WHERE id = %s", (existing[0],))
            is_admin = cur.fetchone()[0]
            
            if is_admin:
                print(f"✅ User '{username}' is already an admin.")
            else:
                # Set as admin
                cur.execute("UPDATE users SET is_admin = TRUE WHERE id = %s", (existing[0],))
                conn.commit()
                print(f"✅ Set existing user '{username}' as admin.")
            
            cur.close()
            conn.close()
            return True
        
        # Hash password
        ph = PasswordHasher()
        password_hash = ph.hash(password)
        
        # Create new user as admin
        cur.execute("""
            INSERT INTO users (username, email, password_hash, is_admin, created_at)
            VALUES (%s, %s, %s, TRUE, CURRENT_TIMESTAMP)
            RETURNING id
        """, (username, email, password_hash))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        
        print(f"✅ Successfully created admin user:")
        print(f"   ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Admin: TRUE")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create_admin_user.py <username> <email> <password>")
        print("\nExample:")
        print("  python create_admin_user.py admin123 admin123@example.com Admin123!")
        print("\nNote: Password must be at least 8 characters with uppercase, lowercase, and number")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    # Validate password
    if len(password) < 8:
        print("❌ Error: Password must be at least 8 characters long")
        sys.exit(1)
    
    print(f"Creating admin user: {username}")
    print("-" * 50)
    
    # Ensure admin column exists
    if not ensure_admin_column():
        print("Failed to ensure admin column exists. Exiting.")
        sys.exit(1)
    
    # Create admin user
    if create_admin_user(username, email, password):
        print("-" * 50)
        print(f"✅ Admin user '{username}' is ready!")
        print("\nThe user can now login and will have admin privileges:")
        print("  - See all groups in the chat system")
        print("  - Delete any group")
        print("  - Delete any review/rating")
        print("  - Delete any message")
    else:
        sys.exit(1)

