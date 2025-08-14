#!/usr/bin/env python3
"""
Database Migration Script for Instagram Meme Bot
Adds missing columns to the memes table
"""

import os
import psycopg2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate_database():
    """Add missing columns to memes table"""
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not found!")
        return False
    
    try:
        # Connect to database
        logger.info("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check current table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'memes' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        
        existing_columns = {row[0]: row[1] for row in cursor.fetchall()}
        logger.info(f"📊 Found {len(existing_columns)} existing columns: {list(existing_columns.keys())}")
        
        # Add missing columns
        migrations = []
        
        if 'uploaded_to_instagram' not in existing_columns:
            migrations.append("ADD COLUMN uploaded_to_instagram BOOLEAN DEFAULT FALSE")
            
        if 'uploaded_at' not in existing_columns:
            migrations.append("ADD COLUMN uploaded_at TIMESTAMP DEFAULT NULL")
            
        if 'instagram_post_id' not in existing_columns:
            migrations.append("ADD COLUMN instagram_post_id VARCHAR(50) DEFAULT NULL")
            
        if migrations:
            migration_sql = "ALTER TABLE memes " + ", ".join(migrations) + ";"
            logger.info(f"🔧 Running migration: {migration_sql}")
            
            cursor.execute(migration_sql)
            conn.commit()
            logger.info("✅ Migration completed successfully")
        else:
            logger.info("✅ No migrations needed - all columns exist")
        
        # Create indexes for better performance
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_memes_uploaded_instagram ON memes(uploaded_to_instagram);",
            "CREATE INDEX IF NOT EXISTS idx_memes_uploaded_at ON memes(uploaded_at);",
            "CREATE INDEX IF NOT EXISTS idx_memes_score ON memes(score DESC);"
        ]
        
        for query in index_queries:
            try:
                cursor.execute(query)
                conn.commit()
                logger.info(f"✅ Index created: {query.split()[4]}")
            except Exception as e:
                logger.warning(f"⚠️ Index creation warning: {e}")
        
        # Show final table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'memes' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        logger.info("📋 Final table structure:")
        for col in columns:
            logger.info(f"   {col[0]} ({col[1]}) - Nullable: {col[2]}, Default: {col[3]}")
        
        # Show current data count
        cursor.execute("SELECT COUNT(*) FROM memes;")
        total_memes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memes WHERE uploaded_to_instagram = TRUE;")
        uploaded_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memes WHERE uploaded_to_instagram IS NULL OR uploaded_to_instagram = FALSE;")
        available_count = cursor.fetchone()[0]
        
        logger.info(f"📊 Memes status:")
        logger.info(f"   Total: {total_memes}")
        logger.info(f"   Uploaded: {uploaded_count}")
        logger.info(f"   Available: {available_count}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Running database migration...")
    success = migrate_database()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        exit(1)
