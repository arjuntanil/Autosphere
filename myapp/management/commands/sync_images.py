import os
from pathlib import Path
from django.core.management.base import BaseCommand
from myapp.models import VehicleFine

class Command(BaseCommand):
    help = 'Sync database image records with actual files on disk'

    def handle(self, *args, **options):
        # Get base directory
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        media_dir = os.path.join(BASE_DIR, 'media')
        violation_images_dir = os.path.join(media_dir, 'violation_images')
        
        self.stdout.write(self.style.SUCCESS(f"Media directory: {media_dir}"))
        self.stdout.write(self.style.SUCCESS(f"Violation images directory: {violation_images_dir}"))
        
        # List files in violation_images directory
        if os.path.exists(violation_images_dir):
            image_files = os.listdir(violation_images_dir)
            self.stdout.write(self.style.SUCCESS(f"Found {len(image_files)} image files on disk"))
            for file in image_files:
                self.stdout.write(f"  - {file}")
        else:
            self.stdout.write(self.style.ERROR(f"Violation images directory does not exist!"))
            return
        
        # Get all fines and update image records
        fines = VehicleFine.objects.all()
        self.stdout.write(self.style.SUCCESS(f"Found {fines.count()} fines in database"))
        
        # 1. Update fines that have images in the database but files don't exist
        for fine in fines:
            if fine.violation_image:
                relative_path = str(fine.violation_image.name).replace('/', os.path.sep)
                disk_path = os.path.join(BASE_DIR, 'media', relative_path)
                
                self.stdout.write(f"Fine ID {fine.id} has image '{fine.violation_image.name}'")
                
                if not os.path.exists(disk_path):
                    self.stdout.write(self.style.WARNING(f"  Image file not found on disk!"))
                    
                    # Find first available image from disk to link to this fine
                    if image_files:
                        new_image_name = image_files[0]
                        fine.violation_image.name = f"violation_images/{new_image_name}"
                        fine.save(update_fields=['violation_image'])
                        self.stdout.write(self.style.SUCCESS(f"  Updated to use '{new_image_name}'"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"  Image file exists on disk"))
            else:
                # Fine has no image
                self.stdout.write(f"Fine ID {fine.id} has no image")
                
                # Link an image if any available
                if image_files:
                    new_image_name = image_files[0]
                    fine.violation_image.name = f"violation_images/{new_image_name}"
                    fine.save(update_fields=['violation_image'])
                    self.stdout.write(self.style.SUCCESS(f"  Added image '{new_image_name}'"))
        
        self.stdout.write(self.style.SUCCESS("Done syncing images!"))
