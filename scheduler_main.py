# Add these imports at the top
import threading
from meme_graphql import app as graphql_app
import uvicorn

# Add this function after your existing functions
def start_graphql_server():
    """Start GraphQL server alongside existing dashboard"""
    graphql_port = int(os.environ.get("GRAPHQL_PORT", 8080))
    logger.info(f"🚀 Starting GraphQL server on port {graphql_port}")
    uvicorn.run(graphql_app, host="0.0.0.0", port=graphql_port)

# In your main() function, add this after starting the health server:
def main():
    # Your existing code...
    
    # Start health server (keep this)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # NEW: Start GraphQL server
    graphql_thread = threading.Thread(target=start_graphql_server, daemon=True)
    graphql_thread.start()
    
    # Rest of your existing code...
