import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from myapp.models import VehicleFine
from reportlab.pdfgen import canvas
from io import BytesIO

class Command(BaseCommand):
    help = 'Add a test PDF to the first fine in the system'

    def handle(self, *args, **options):
        # Get base directory
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        media_dir = os.path.join(BASE_DIR, 'media')
        violation_docs_dir = os.path.join(media_dir, 'violation_documents')
        
        # Ensure directories exist
        os.makedirs(violation_docs_dir, exist_ok=True)
        
        self.stdout.write(self.style.SUCCESS(f"Media directory: {media_dir}"))
        self.stdout.write(self.style.SUCCESS(f"Violation documents directory: {violation_docs_dir}"))
        
        # Find fines in the system
        fines = VehicleFine.objects.all()
        if not fines.exists():
            self.stdout.write(self.style.ERROR("No fines found in the system!"))
            return
            
        fine = fines.first()
        self.stdout.write(self.style.SUCCESS(f"Found fine ID {fine.id} for vehicle {fine.vehicle.registration_number}"))
        
        # Generate a PDF
        self.stdout.write("Generating sample PDF document...")
        buffer = BytesIO()
        
        # Create the PDF
        p = canvas.Canvas(buffer)
        p.setFont("Helvetica", 14)
        p.drawString(100, 800, f"VIOLATION DOCUMENT - FINE #{fine.id}")
        p.setFont("Helvetica", 12)
        p.drawString(100, 780, f"Vehicle: {fine.vehicle.registration_number}")
        p.drawString(100, 760, f"Violation Type: {fine.violation_type}")
        p.drawString(100, 740, f"Fine Amount: ₹{fine.fine_amount}")
        p.drawString(100, 720, f"Location: {fine.location}")
        p.drawString(100, 700, f"Issued By: {fine.imposed_by.get_full_name() if fine.imposed_by else 'Unknown'}")
        p.drawString(100, 680, f"Issued Date: {fine.imposed_date.strftime('%d %b %Y')}")
        p.drawString(100, 660, f"Due Date: {fine.due_date.strftime('%d %b %Y')}")
        p.drawString(100, 640, f"Status: {fine.payment_status}")
        
        p.setFont("Helvetica-Bold", 11)
        p.drawString(100, 600, "Description:")
        p.setFont("Helvetica", 11)
        description_lines = [fine.description[i:i+70] for i in range(0, len(fine.description or "No description"), 70)]
        for i, line in enumerate(description_lines):
            p.drawString(120, 580 - (i * 20), line)
            
        p.drawString(100, 300, "This is an automatically generated document.")
        p.drawString(100, 280, "Please contact the RTO office for any clarifications.")
        p.save()
        
        # Get the PDF from the buffer
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Save to the model
        filename = f"violation_document_{fine.id}.pdf"
        
        # First, manually save the file to disk to ensure it exists
        file_path = os.path.join(violation_docs_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(pdf_content)
        
        self.stdout.write(self.style.SUCCESS(f"Manually saved PDF to: {file_path}"))
        
        # Update the model with the relative path
        relative_path = f"violation_documents/{filename}"  # Always use forward slashes for database
        fine.violation_document.name = relative_path
        fine.save(update_fields=['violation_document'])
        
        self.stdout.write(self.style.SUCCESS(f"Added test PDF document to fine ID {fine.id}"))
        
        # Verify the file exists on disk
        document_path = os.path.join(BASE_DIR, 'media', relative_path.replace('/', os.path.sep))
        if os.path.exists(document_path):
            self.stdout.write(self.style.SUCCESS(f"PDF document saved successfully at: {document_path}"))
            self.stdout.write(self.style.SUCCESS(f"File size: {os.path.getsize(document_path)} bytes"))
        else:
            self.stdout.write(self.style.ERROR(f"File not found at: {document_path}"))
            
        # Double-check database record
        refreshed_fine = VehicleFine.objects.get(id=fine.id)
        self.stdout.write(self.style.SUCCESS(f"Database record updated - Document name: {refreshed_fine.violation_document.name}"))
