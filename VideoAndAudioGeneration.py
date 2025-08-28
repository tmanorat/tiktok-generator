from pathlib import Path
import requests
import feedparser
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent/".env", override=True)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
import re
import moviepy
import time
import random
from pathlib import Path

# ===== CONFIGURATION SECTION - EDIT THESE FOR DIFFERENT NICHES =====

# Reddit RSS URL - Change this for different niches
RSS_URL = 'https://www.reddit.com/r/selfimprovement/hot.rss'

# Script generation prompt - Customize for your niche
SCRIPT_PROMPT_TEMPLATE = """
Create a 55-65 second motivational script for a men's self-improvement TikTok video based on this Reddit post. 

Requirements:
- Write in first-person, confident tone
- Include 4-5 actionable tips or insights
- Focus on mindset, confidence, social skills, or personal growth
- End with strong engagement hook like "What's your biggest challenge?" or "Drop your wins below!"
- Target 280-350 words for 60-second delivery
- Make it conversational, authentic, and inspiring
- Avoid repetitive phrases
- Include personal anecdotes or relatable scenarios

Reddit Post: {post_content}
"""

# Image generation prompts - Customize for your niche
IMAGE_PROMPTS_TEMPLATE = [
    "A confident young man in his 20s-30s, modern lifestyle, success mindset, clean aesthetic, motivational energy, professional lighting, NO TEXT, NO WORDS, photorealistic portrait, inspired by: {title}",
    "Minimalist illustration of personal growth and success, modern design, inspiring colors, upward progress, achievement theme, clean background, NO TEXT, NO LETTERS, NO WORDS, abstract symbols only",
    "Professional young man working on self-improvement, gym or office setting, determined expression, high quality, cinematic lighting, NO TEXT, inspired by: {title}",
    "Abstract representation of mental strength and confidence, geometric shapes, motivational colors like blue and gold, modern minimalist design, NO WORDS, NO TEXT",
    "Successful man in casual setting, natural smile, approachable but confident, lifestyle photography, warm lighting, NO TEXT OR WORDS",
    "Inspirational workspace or nature scene, books, goals, personal development theme, clean aesthetic, NO TEXT ANYWHERE"
]

# ===== END CONFIGURATION SECTION =====

# Choose TTS provider: 'openai' or 'elevenlabs'
TTS_PROVIDER = 'elevenlabs'  # Change this to switch providers

# Fix PIL/Pillow compatibility issue before importing moviepy
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

# Configure ImageMagick path for Windows
import os
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent/".env", override=True)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
imagemagick_paths = [
    r"C:\Program Files\ImageMagick-7.1.2-0\magick.exe",
    r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe",
    r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe", 
    r"C:\Program Files (x86)\ImageMagick-7.1.2-0\magick.exe"
]

for path in imagemagick_paths:
    if os.path.exists(path):
        os.environ['IMAGEMAGICK_BINARY'] = path
        print(f"âœ… Found ImageMagick at: {path}")
        break
else:
    # If not found at standard paths, try to use system PATH
    import shutil
    magick_path = shutil.which('magick')
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
        print(f"âœ… Found ImageMagick via PATH at: {magick_path}")
    else:
        print("âš ï¸ ImageMagick not found - subtitles may fail")

from moviepy import ImageClip, concatenate_videoclips, AudioFileClip

# Your OpenAI API key (use environment variables in production)
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_audio_elevenlabs(text, output_path):
    """Generate audio using ElevenLabs TTS"""
    # Popular male voices for motivation content
    voice_options = {
        "Adam": "pNInz6obpgDQGcFmaJgB",  # Deep, confident male
        "Antoni": "ErXwobaYiN019PkySvjV",  # Warm, well-rounded male
        "Josh": "TxGEqnHWrfWFTfGW9XjX",  # Deep, authoritative male
        "Sam": "yoZ06aMxZJJ28mfd3POQ"   # Raspy, casual male
    }
    
    voice_id = voice_options["Adam"]  # Default to Adam for motivation content
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",  # Fastest, cheapest model
        "voice_settings": {
            "stability": 0.6,      # More stable/consistent
            "similarity_boost": 0.8, # More similar to original voice
            "style": 0.2,          # Slight style enhancement
            "use_speaker_boost": True
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
        
    except Exception as e:
        print(f"âŒ ElevenLabs TTS error: {e}")
        return False

def generate_audio_openai(text, output_path):
    """Generate audio using OpenAI TTS (fallback)"""
    try:
        audio_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text,
            speed=1.0
        )
        
        with open(output_path, 'wb') as f:
            for chunk in audio_response.iter_bytes():
                f.write(chunk)
        return True
        
    except Exception as e:
        print(f"âŒ OpenAI TTS error: {e}")
        return False



def test_openai_connection():
    """Test OpenAI connection before proceeding"""
    try:
        client.models.list()
        return True
    except Exception as e:
        print(f"âŒ OpenAI connection failed: {e}")
        return False

def main():
    print("ðŸš€ Starting video generation...")
    
    # Test OpenAI connection first to avoid wasting time
    if not test_openai_connection():
        print("âŒ Please check your OpenAI API key and connection.")
        return
    
    # Step 1: Fetch and parse RSS to get top post
    print("ðŸ“¡ Fetching Reddit posts...")
    
    # Headers to bypass Reddit rate limiting
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Retry logic for rate limiting
    max_retries = 3
    feed = None
    for attempt in range(max_retries):
        try:
            # Add random delay to avoid seeming like a bot
            if attempt > 0:
                wait_time = random.uniform(5, 15)
                print(f"â³ Waiting {wait_time:.1f} seconds before retry {attempt + 1}...")
                time.sleep(wait_time)
            
            response = requests.get(RSS_URL, headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            print("âœ… RSS feed fetched successfully!")
            break
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"âš ï¸ Rate limited (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print("âŒ Max retries exceeded. Try again later or use a VPN.")
                    return
            else:
                print(f"âŒ HTTP Error: {e}")
                return
        except Exception as e:
            print(f"âŒ Error fetching RSS feed: {e}")
            if attempt == max_retries - 1:
                return
    
    if not feed or not feed.entries:
        print("âŒ No posts found. Exiting.")
        return
    
    # Pick the top post
    top_entry = feed.entries[0]
    title = top_entry.title
    author = getattr(top_entry, 'author', 'Unknown')
    link = getattr(top_entry, 'link', '')
    summary = getattr(top_entry, 'description', title)[:400]
    post_content = f"Title: {title}\nAuthor: {author}\nSummary: {summary}"
    
    print(f"âœ… Selected post: {title[:50]}...")
    
    # Step 2: Generate video script with ChatGPT API
    print("ðŸ§  Generating script...")
    script_prompt = SCRIPT_PROMPT_TEMPLATE.format(post_content=post_content)
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": script_prompt}],
            max_tokens=400,  # Increased for longer scripts
            temperature=0.8
        )
        script = completion.choices[0].message.content.strip()
        print("âœ… Script generated!")
        print(f"Script preview: {script[:100]}...")
    except Exception as e:
        print(f"âŒ Error generating script: {e}")
        return
    
    # Step 3: Generate audio narration
    print("ðŸŽµ Generating narration...")
    audio_path = "narration.mp3"
    
    if TTS_PROVIDER == 'elevenlabs' and ELEVENLABS_API_KEY:
        print("ðŸŽ¤ Using ElevenLabs TTS...")
        audio_success = generate_audio_elevenlabs(script, audio_path)
        if not audio_success:
            print("âš ï¸ ElevenLabs failed, falling back to OpenAI...")
            audio_success = generate_audio_openai(script, audio_path)
    else:
        print("ðŸŽ¤ Using OpenAI TTS...")
        audio_success = generate_audio_openai(script, audio_path)
    
    if not audio_success:
        print("âŒ Audio generation failed!")
        return
    
    print("âœ… Audio generated!")
    
    # Step 4: Generate 5+ images with DALL-E for smooth transitions
    print("ðŸŽ¨ Generating images...")
    
    # Generate image prompts based on template
    image_prompts = [prompt.format(title=title[:60]) for prompt in IMAGE_PROMPTS_TEMPLATE]
    
    image_paths = []
    for i, prompt in enumerate(image_prompts):
        try:
            image_response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1792",  # Vertical for shorts
                quality="standard",
                n=1
            )
            
            image_url = image_response.data[0].url
            image_data = requests.get(image_url, timeout=30).content
            image_path = f"image_{i}.png"
            
            with open(image_path, "wb") as f:
                f.write(image_data)
            image_paths.append(image_path)
            print(f"âœ… Image {i+1} generated!")
            
        except Exception as e:
            print(f"âš ï¸ Error generating image {i}: {e}")
            continue
    
    if not image_paths:
        print("âŒ No images generated. Exiting.")
        return
    
    # Step 5: Create video with MoviePy
    print("ðŸŽ¬ Assembling video...")
    
    try:
        # Load audio
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        print(f"Audio duration: {audio_duration:.2f} seconds")
        
        # Create video with animated background images (Ken Burns effect)
        background_clips = []
        
        # Calculate durations
        img_duration = audio_duration / len(image_paths)
        
        print(f"Each image duration: {img_duration:.2f}s with animation effects")
        
        # Create animated background clips
        for i, img_path in enumerate(image_paths):
            try:
                # Load image larger than needed for animation room
                img_clip = ImageClip(img_path, duration=img_duration)
                
                # Different animation types for variety
                animation_type = i % 4
                
                if animation_type == 0:
                    # Slow zoom in
                    img_clip = (img_clip.resize(height=2100)  # Start larger
                               .resize(lambda t: 1 - 0.1 * t / img_duration)  # Zoom in slowly
                               .set_position('center'))
                
                elif animation_type == 1:
                    # Slow zoom out  
                    img_clip = (img_clip.resize(height=1900)  # Start smaller
                               .resize(lambda t: 1 + 0.1 * t / img_duration)  # Zoom out slowly
                               .set_position('center'))
                
                elif animation_type == 2:
                    # Pan left to right
                    img_clip = (img_clip.resize(height=1920).resize(width=1200)  # Wider for panning
                               .set_position(lambda t: (-60 + 120 * t / img_duration, 'center')))
                
                else:
                    # Pan right to left
                    img_clip = (img_clip.resize(height=1920).resize(width=1200)  # Wider for panning
                               .set_position(lambda t: (60 - 120 * t / img_duration, 'center')))
                
                background_clips.append(img_clip)
                print(f"âœ… Animated image {i+1} created (animation type {animation_type})")
                
            except Exception as clip_error:
                print(f"âš ï¸ Error animating image {i}: {clip_error}")
                # Simple fallback without animation
                simple_clip = ImageClip(img_path, duration=img_duration).resize(height=1920).set_position('center')
                background_clips.append(simple_clip)
        
        # Concatenate background clips (no crossfade, just cuts)
        if len(background_clips) > 1:
            background_video = concatenate_videoclips(background_clips, method="compose")
        else:
            background_video = background_clips[0]
        
        print(f"âœ… Created video with {len(background_clips)} animated images")
            
        # Set audio
        final_video = background_video.set_audio(audio_clip)
        
        # Export video
        output_path = f"self_improvement_video_{int(time.time())}.mp4"
        final_video.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        print(f"ðŸŽ‰ Video saved to: {output_path}")
        
    except Exception as e:
        print(f"âŒ Error creating video: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        cleanup_files = image_paths + [audio_path, "temp-audio.m4a"]
        for path in cleanup_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        print("âœ… Cleanup completed!")

if __name__ == "__main__":
    main()










