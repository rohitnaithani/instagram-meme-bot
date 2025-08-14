import os
import logging
from instagram_private_api import Client as InstagramAPI
from instagram_private_api.errors import *
import random
import time

# Import your database functions
from cloud_meme_fetcher import get_meme_for_posting, mark_meme_as_posted, cleanup_temp_file

logger = logging.getLogger(__name__)

# Instagram credentials from environment
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

def get_instagram_client():
    """Get Instagram client with error handling"""
    try:
        client = InstagramAPI(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        logger.info(f"✅ Instagram login successful: {INSTAGRAM_USERNAME}")
        return client
    except Exception as e:
        logger.error(f"❌ Instagram login failed: {e}")
        return None

def generate_hashtags():
    """Generate relevant hashtags"""
    hashtags = [
        "#memes", "#dankmemes", "#funny", "#humor", "#comedy", 
        "#meme", "#lol", "#haha", "#entertainment", "#viral",
        "#funnyvideos", "#memesdaily", "#laughs", "#jokes", "#fun"
    ]
    
    # Select random hashtags (Instagram allows up to 30)
    selected = random.sample(hashtags, min(10, len(hashtags)))
    return " ".join(selected)

def post_to_instagram():
    """Post next available meme to Instagram"""
    logger.info("📱 Starting Instagram post...")
    
    # Get Instagram client
    client = get_instagram_client()
    if not client:
        return False
    
    # Get next meme from database
    meme, temp_file = get_meme_for_posting(prefer_images=True)
    
    if not meme or not temp_file:
        logger.info("📭 No memes available for posting")
        return False
    
    try:
        # Prepare caption
        title = meme['title'][:100]  # Truncate long titles
        hashtags = generate_hashtags()
        caption = f"{title}\n\n{hashtags}"
        
        # Post based on file type
        if meme['file_type'] == 'image':
            logger.info(f"📸 Posting image: {title[:30]}...")
            
            # Upload image
            result = client.photo_upload(
                temp_file,
                caption=caption
            )
            
        elif meme['file_type'] == 'video':
            logger.info(f"🎥 Posting video: {title[:30]}...")
            
            # Upload video
            result = client.video_upload(
                temp_file,
                caption=caption
            )
        
        else:
            logger.error(f"❌ Unknown file type: {meme['file_type']}")
            return False
        
        # Check if upload was successful
        if result and 'media' in result:
            media_id = result['media']['id']
            logger.info(f"✅ Posted successfully! Media ID: {media_id}")
            
            # Mark as posted in database
            mark_meme_as_posted(meme['post_id'])
            
            # Clean up temp file
            cleanup_temp_file(temp_file)
            
            return True
        else:
            logger.error("❌ Upload failed - no media ID returned")
            return False
            
    except ClientLoginError as e:
        logger.error(f"❌ Instagram login error: {e}")
        return False
        
    except ClientError as e:
        logger.error(f"❌ Instagram client error: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error during Instagram post: {e}")
        return False
        
    finally:
        # Always clean up temp file
        cleanup_temp_file(temp_file)

def test_instagram_connection():
    """Test Instagram connection without posting"""
    logger.info("🧪 Testing Instagram connection...")
    
    client = get_instagram_client()
    if not client:
        return False
    
    try:
        # Get user info to verify connection
        user_info = client.current_user()
        logger.info(f"✅ Instagram connection test successful!")
        logger.info(f"   Account: {user_info['username']}")
        logger.info(f"   Followers: {user_info['follower_count']}")
        logger.info(f"   Following: {user_info['following_count']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Instagram connection test failed: {e}")
        return False

if __name__ == "__main__":
    # Test the posting system
    print("🧪 Testing Instagram posting system...")
    
    # Test connection first
    if test_instagram_connection():
        print("✅ Connection test passed!")
        
        # Uncomment to test actual posting
        # print("📱 Testing post...")
        # success = post_to_instagram()
        # print(f"Post result: {success}")
    else:
        print("❌ Connection test failed!")
