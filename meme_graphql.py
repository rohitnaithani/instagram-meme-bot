#!/usr/bin/env python3
"""
GraphQL API for Meme Upload Management
Keeps your existing scraper untouched!
"""

import os
import subprocess
import sys
from datetime import datetime
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

DATABASE_URL = os.getenv("DATABASE_URL")

# Simple database helper
def get_memes_from_db(uploaded_only=False, limit=20):
    """Get memes from your existing database"""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        query = """
        SELECT id, post_id, title, url, file_type, score,
               COALESCE(uploaded_to_instagram, FALSE) as uploaded,
               uploaded_at::text as uploaded_at
        FROM memes 
        WHERE url IS NOT NULL
        """
        
        if uploaded_only is not None:
            query += f" AND COALESCE(uploaded_to_instagram, FALSE) = {uploaded_only}"
            
        query += f" ORDER BY score DESC LIMIT {limit}"
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        print(f"Database error: {e}")
        return []

# GraphQL Types
@strawberry.type
class SimpleMeme:
    id: int
    title: str
    file_type: str
    score: int
    uploaded: bool
    url: str

@strawberry.type
class QuickStats:
    total_available: int
    total_uploaded: int
    images: int
    videos: int

@strawberry.type
class UploadResponse:
    success: bool
    message: str

# GraphQL Schema
@strawberry.type
class Query:
    @strawberry.field
    def available_memes(self, limit: int = 10) -> List[SimpleMeme]:
        """Get memes ready to upload"""
        memes = get_memes_from_db(uploaded_only=False, limit=limit)
        return [SimpleMeme(
            id=m['id'],
            title=m['title'][:50] + ('...' if len(m['title']) > 50 else ''),
            file_type=m['file_type'],
            score=m['score'],
            uploaded=m['uploaded'],
            url=m['url']
        ) for m in memes if not m['uploaded']]
    
    @strawberry.field
    def uploaded_memes(self, limit: int = 10) -> List[SimpleMeme]:
        """Get already uploaded memes"""
        memes = get_memes_from_db(uploaded_only=True, limit=limit)
        return [SimpleMeme(
            id=m['id'],
            title=m['title'][:50] + ('...' if len(m['title']) > 50 else ''),
            file_type=m['file_type'],
            score=m['score'],
            uploaded=m['uploaded'],
            url=m['url']
        ) for m in memes]
    
    @strawberry.field
    def stats(self) -> QuickStats:
        """Get quick statistics"""
        try:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE COALESCE(uploaded_to_instagram, FALSE) = FALSE) as available,
                COUNT(*) FILTER (WHERE uploaded_to_instagram = TRUE) as uploaded,
                COUNT(*) FILTER (WHERE file_type = 'image') as images,
                COUNT(*) FILTER (WHERE file_type = 'video') as videos
            FROM memes WHERE url IS NOT NULL
            """)
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return QuickStats(
                total_available=result['available'] or 0,
                total_uploaded=result['uploaded'] or 0,
                images=result['images'] or 0,
                videos=result['videos'] or 0
            )
        except Exception as e:
            return QuickStats(total_available=0, total_uploaded=0, images=0, videos=0)

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def upload_next_meme(self) -> UploadResponse:
        """Upload the next best meme (uses your existing uploader)"""
        try:
            result = subprocess.run([
                sys.executable, "cloud_instagram_uploader.py"
            ], capture_output=True, text=True, timeout=900)
            
            if result.returncode == 0:
                return UploadResponse(
                    success=True,
                    message="✅ Meme uploaded successfully!"
                )
            else:
                return UploadResponse(
                    success=False,
                    message=f"❌ Upload failed: {result.stderr[:100]}"
                )
        except Exception as e:
            return UploadResponse(
                success=False,
                message=f"❌ Error: {str(e)[:100]}"
            )
    
    @strawberry.mutation
    async def fetch_new_memes(self) -> UploadResponse:
        """Fetch new memes (uses your existing fetcher)"""
        try:
            result = subprocess.run([
                sys.executable, "cloud_meme_fetcher.py"
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                return UploadResponse(
                    success=True,
                    message="✅ New memes fetched successfully!"
                )
            else:
                return UploadResponse(
                    success=False,
                    message=f"❌ Fetch failed: {result.stderr[:100]}"
                )
        except Exception as e:
            return UploadResponse(
                success=False,
                message=f"❌ Error: {str(e)[:100]}"
            )

# Create FastAPI app
app = FastAPI(title="Meme Bot GraphQL API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

# Add GraphQL
schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema, graphiql=True)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
async def root():
    return {"message": "GraphQL at /graphql"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
