#!/usr/bin/env python3
"""
Setup script for chat system database tables
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from datetime import datetime

def setup_chat_database():
    """Create chat-related database tables"""
    
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'dbname': 'flavorquest',
        'user': 'flavoruser',
        'password': 'securepass'
    }
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        print("Connected to database successfully")
        
        # Create groups table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        print("✅ Created groups table")
        
        # Create group_members table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id SERIAL PRIMARY KEY,
                group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('admin', 'member')),
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(group_id, user_id)
            )
        """)
        print("✅ Created group_members table")
        
        # Create messages table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'file', 'system')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_edited BOOLEAN DEFAULT FALSE,
                is_deleted BOOLEAN DEFAULT FALSE
            )
        """)
        print("✅ Created messages table")
        
        # Create indexes for better performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON group_members(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_group_id ON messages(group_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
        print("✅ Created database indexes")
        
        # Create triggers for updated_at timestamps
        cur.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        cur.execute("""
            DROP TRIGGER IF EXISTS update_groups_updated_at ON groups;
            CREATE TRIGGER update_groups_updated_at 
                BEFORE UPDATE ON groups 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
        
        cur.execute("""
            DROP TRIGGER IF EXISTS update_messages_updated_at ON messages;
            CREATE TRIGGER update_messages_updated_at 
                BEFORE UPDATE ON messages 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
        print("✅ Created update triggers")
        
        # Insert some sample data for testing
        print("\n📝 Inserting sample data...")
        
        # Check if we have users to create sample groups
        cur.execute("SELECT id, username FROM users LIMIT 3")
        users = cur.fetchall()
        
        if len(users) >= 2:
            # Create a sample group
            cur.execute("""
                INSERT INTO groups (name, description, created_by) 
                VALUES ('Food Lovers', 'A group for food enthusiasts to share restaurant recommendations', %s)
                ON CONFLICT DO NOTHING
            """, (users[0][0],))
            
            # Get the group ID
            cur.execute("SELECT id FROM groups WHERE name = 'Food Lovers'")
            group_result = cur.fetchone()
            
            if group_result:
                group_id = group_result[0]
                
                # Add users to the group
                for user_id, username in users[:2]:  # Add first 2 users
                    cur.execute("""
                        INSERT INTO group_members (group_id, user_id, role) 
                        VALUES (%s, %s, %s)
                        ON CONFLICT (group_id, user_id) DO NOTHING
                    """, (group_id, user_id, 'admin' if user_id == users[0][0] else 'member'))
                
                # Add some sample messages
                sample_messages = [
                    (group_id, users[0][0], "Welcome to Food Lovers! 🍽️"),
                    (group_id, users[0][0], "Share your favorite restaurants here!"),
                    (group_id, users[1][0], "Thanks for creating this group! I love trying new places."),
                    (group_id, users[0][0], "Has anyone tried the new Italian place downtown?"),
                ]
                
                for group_id, user_id, content in sample_messages:
                    cur.execute("""
                        INSERT INTO messages (group_id, user_id, content) 
                        VALUES (%s, %s, %s)
                    """, (group_id, user_id, content))
                
                print("✅ Created sample group 'Food Lovers' with messages")
        
        print("\n🎉 Chat database setup completed successfully!")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
    
    return True

if __name__ == "__main__":
    setup_chat_database()
