import os
import io
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from myapp.models import VehicleFine
from PIL import Image

class Command(BaseCommand):
    help = 'Debug script for testing image upload functionality'

    def handle(self, *args, **options):
        # Create media directories if they don't exist
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        media_dir = os.path.join(BASE_DIR, 'media')
        violation_images_dir = os.path.join(media_dir, 'violation_images')

        if not os.path.exists(media_dir):
            os.makedirs(media_dir)
            self.stdout.write(self.style.SUCCESS(f"Created media directory: {media_dir}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Media directory exists: {media_dir}"))

        if not os.path.exists(violation_images_dir):
            os.makedirs(violation_images_dir)
            self.stdout.write(self.style.SUCCESS(f"Created violation_images directory: {violation_images_dir}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Violation images directory exists: {violation_images_dir}"))

        # Check existing fines
        self.stdout.write("\n--- EXISTING FINES ---")
        fines_count = VehicleFine.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Total fines in database: {fines_count}"))

        for fine in VehicleFine.objects.all():
            image_name = fine.violation_image.name if fine.violation_image else "No image"
            self.stdout.write(f"Fine ID: {fine.id}, Vehicle: {fine.vehicle.registration_number}, Image: {image_name}")
            
            # Check if the image file exists on disk
            if fine.violation_image:
                full_path = os.path.join(BASE_DIR, "media", fine.violation_image.name)
                exists = os.path.exists(full_path)
                self.stdout.write(f"  Image path: {full_path}")
                self.stdout.write(f"  Image exists on disk: {exists}")

        # Update the fine with a test image if there are any fines
        if fines_count > 0:
            self.stdout.write("\n--- UPDATING FIRST FINE WITH TEST IMAGE ---")
            fine = VehicleFine.objects.first()
            
            # Create a 100x100 red image
            img = Image.new('RGB', (100, 100), color='red')
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG')
            
            # Save to the model
            fine.violation_image.save(
                f'test_violation_{fine.id}.jpg',
                ContentFile(buffer.getvalue())
            )
            
            self.stdout.write(self.style.SUCCESS(f"Updated fine ID {fine.id} with test image"))
            self.stdout.write(f"Image name: {fine.violation_image.name}")
            
            # Verify the image exists
            full_path = os.path.join(BASE_DIR, "media", fine.violation_image.name)
            if os.path.exists(full_path):
                self.stdout.write(self.style.SUCCESS(f"SUCCESS: Test image created at {full_path}"))
            else:
                self.stdout.write(self.style.ERROR(f"ERROR: Failed to create test image at {full_path}"))
