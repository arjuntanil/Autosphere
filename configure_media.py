import os
import sys
import importlib.util
from pathlib import Path

# Get the project directory
project_dir = Path(__file__).resolve().parent

# Function to check if a directory exists and create it if it doesn't
def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")

# Create media directories
media_root = os.path.join(project_dir, 'media')
violation_images_dir = os.path.join(media_root, 'violation_images')

ensure_directory_exists(media_root)
ensure_directory_exists(violation_images_dir)

# Check Django settings
try:
    # Try to load the settings module
    settings_path = os.path.join(project_dir, 'autosphere', 'settings.py')
    if not os.path.exists(settings_path):
        print(f"ERROR: Settings file not found at {settings_path}")
        sys.exit(1)
        
    # Load settings as a module
    spec = importlib.util.spec_from_file_location("settings", settings_path)
    settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)
    
    # Check if MEDIA_URL and MEDIA_ROOT are defined
    media_url_defined = hasattr(settings, 'MEDIA_URL')
    media_root_defined = hasattr(settings, 'MEDIA_ROOT')
    
    print(f"MEDIA_URL defined in settings: {media_url_defined}")
    print(f"MEDIA_ROOT defined in settings: {media_root_defined}")
    
    if media_url_defined:
        print(f"Current MEDIA_URL: {settings.MEDIA_URL}")
    if media_root_defined:
        print(f"Current MEDIA_ROOT: {settings.MEDIA_ROOT}")
        
    # Create settings update instructions
    with open('media_settings_instructions.txt', 'w') as f:
        f.write("# Django Media Configuration Instructions\n\n")
        
        # Settings.py instructions
        f.write("## 1. Add to settings.py\n")
        f.write("Add the following lines to your autosphere/settings.py file:\n\n")
        f.write("```python\n")
        f.write("# Media files (Uploaded files)\n")
        f.write("MEDIA_URL = '/media/'\n")
        f.write(f"MEDIA_ROOT = os.path.join(BASE_DIR, 'media')\n")
        f.write("```\n\n")
        
        # URLs.py instructions
        f.write("## 2. Update autosphere/urls.py\n")
        f.write("Add the following imports at the top of the file:\n\n")
        f.write("```python\n")
        f.write("from django.conf import settings\n")
        f.write("from django.conf.urls.static import static\n")
        f.write("```\n\n")
        
        f.write("Then add this code at the end of the file, after the urlpatterns list:\n\n")
        f.write("```python\n")
        f.write("if settings.DEBUG:\n")
        f.write("    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)\n")
        f.write("```\n\n")
        
        # Restart instructions
        f.write("## 3. Restart the server\n")
        f.write("After making these changes, restart your Django server:\n\n")
        f.write("```\n")
        f.write("python manage.py runserver\n")
        f.write("```\n")
    
    print("Created media_settings_instructions.txt with configuration details")
        
except Exception as e:
    print(f"Error checking settings: {str(e)}")

print("\nTo fix the image viewing/downloading issue, follow these steps:")
print("1. Check if you have Pillow installed for image processing")
print("   Run: pip install pillow")
print("2. Follow the instructions in the media_settings_instructions.txt file")
print("3. Restart your Django server")
