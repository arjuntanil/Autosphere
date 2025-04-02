"""
Media configuration helper for AutoSphere
Run this script to ensure media directories are properly set up
and to verify media settings
"""
import os
import sys
from pathlib import Path

# Add project directory to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Create necessary media directories
media_dir = os.path.join(BASE_DIR, 'media')
violation_docs_dir = os.path.join(media_dir, 'violation_documents')

# Create directories if they don't exist
os.makedirs(media_dir, exist_ok=True)
os.makedirs(violation_docs_dir, exist_ok=True)

print(f"Media directory: {media_dir}")
print(f"Violation documents directory: {violation_docs_dir}")

# Check if directories exist
print(f"Media directory exists: {os.path.exists(media_dir)}")
print(f"Violation documents directory exists: {os.path.exists(violation_docs_dir)}")

# Check if any files exist in the violation_documents directory
if os.path.exists(violation_docs_dir):
    files = os.listdir(violation_docs_dir)
    print(f"Files in violation_documents directory: {len(files)}")
    for file in files:
        file_path = os.path.join(violation_docs_dir, file)
        print(f"  - {file} ({os.path.getsize(file_path)} bytes)")
else:
    print("Violation documents directory does not exist")

# Print recommendation
print("\nImportant settings for media files:")
print("In your settings.py, ensure you have:")
print("MEDIA_URL = '/media/'")
print(f"MEDIA_ROOT = os.path.join(BASE_DIR, 'media')")
print("\nIn your urls.py, ensure you have:")
print("from django.conf import settings")
print("from django.conf.urls.static import static")
print("urlpatterns = [...] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)")
