"""
Script to fix all indentation issues in views.py file
"""

def fix_impose_fine():
    """Fix the impose_fine function indentation"""
    with open('myapp/views.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the properly indented impose_fine function
    fixed_function = '''@login_required
def impose_fine(request):
    """View for RTO users to impose fines on vehicles"""
    if not request.user.user_type == 'RTO':
        messages.error(request, "You do not have permission to impose fines")
        return redirect('home')
    
    if request.method == 'POST':
        form = FineForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Get or validate vehicle
                reg_number = form.cleaned_data['vehicle_registration_number']
                
                # Normalize the registration number (remove spaces, convert to uppercase)
                normalized_reg = normalize_registration_number(reg_number)
                if not normalized_reg:
                    messages.error(request, f"Invalid registration number format: {reg_number}")
                    return render(request, 'impose_fine.html', {'form': form})
                
                # Try to find the vehicle with the normalized registration number
                try:
                    vehicle = Vehicle.objects.get(registration_number=normalized_reg)
                except Vehicle.DoesNotExist:
                    # Try with the original input as a fallback
                    vehicle = Vehicle.objects.get(registration_number=reg_number)
                
                # Use transaction to ensure all operations succeed or fail together
                with transaction.atomic():
                    # Create the fine object but don't save yet
                    fine = form.save(commit=False)
                    fine.vehicle = vehicle
                    fine.imposed_by = request.user
                    
                    # Save the fine object to generate ID
                    fine.save()
                
                    # Handle multiple file uploads
                    uploaded_files = request.FILES.getlist('violation_documents')
                    if uploaded_files:
                        upload_count = 0
                        from pathlib import Path
                        from django.conf import settings
                        
                        # Get media root
                        media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(Path(__file__).resolve().parent.parent, 'media'))
                        
                        # Create directory for storing violation documents
                        fine_docs_dir = os.path.join(media_root, f'violation_documents/{fine.id}')
                        os.makedirs(fine_docs_dir, exist_ok=True)
                        
                        # Process each uploaded file
                        for uploaded_file in uploaded_files:
                            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
                            
                            if file_ext not in allowed_extensions:
                                messages.warning(request, f"Skipped file '{uploaded_file.name}' - invalid format. Only PDF, JPG, JPEG, PNG are allowed.")
                                continue
                                
                            # Check file size (limit to 5MB)
                            if uploaded_file.size > 5 * 1024 * 1024:  # 5MB in bytes
                                messages.warning(request, f"Skipped file '{uploaded_file.name}' - exceeds 5MB size limit.")
                                continue
                                
                            # Create a new ViolationDocument instance
                            document = ViolationDocument(
                                fine=fine,
                                file=uploaded_file,
                                original_filename=uploaded_file.name
                            )
                            document.save()
                            upload_count += 1
                        
                        if upload_count > 0:
                            messages.success(request, f"{upload_count} document(s) uploaded successfully")
                        else:
                            messages.warning(request, "No valid documents were uploaded. Please try again with supported formats (PDF, JPG, JPEG, PNG) under 5MB each.")
                
                # Create notification for users who have personalized this vehicle
                UserNotification.create_fine_notification(fine)
                
                messages.success(request, f"Fine successfully imposed on vehicle {vehicle.registration_number}")
                return redirect('rto_fine_list')
            except Vehicle.DoesNotExist:
                messages.error(request, f"No vehicle found with registration number {reg_number}")
    else:
        form = FineForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'impose_fine.html', context)
'''

    # Find the start and end of the function
    start_idx = content.find("@login_required\ndef impose_fine(request):")
    next_func = content.find("def rto_fine_list(request):", start_idx)
    
    if start_idx != -1 and next_func != -1:
        # Replace the function
        new_content = content[:start_idx] + fixed_function + content[next_func:]
        with open('myapp/views.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Fixed impose_fine function indentation")
    else:
        print("Could not find impose_fine function")

def fix_rto_modification_requests():
    """Fix the rto_modification_requests function indentation"""
    with open('myapp/views.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the problematic section
    for i, line in enumerate(lines):
        if "# Filter requests based on RTO jurisdiction" in line:
            # Fix indentation for the next few lines
            if i+2 < len(lines) and "requests = VehicleModificationRequest.objects.filter(" in lines[i+2]:
                lines[i+2] = "    requests = VehicleModificationRequest.objects.filter(\n"
                # Make sure next lines are also properly indented
                if i+3 < len(lines):
                    lines[i+3] = "        vehicle__registration_number__startswith=f\"KL {rto_reg_number}\"\n"
                if i+4 < len(lines):
                    lines[i+4] = "    ).order_by('-created_at')\n"
    
    # Write the fixed content back
    with open('myapp/views.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Fixed rto_modification_requests function indentation")

if __name__ == "__main__":
    fix_impose_fine()
    fix_rto_modification_requests()
    print("All indentation issues fixed!") 