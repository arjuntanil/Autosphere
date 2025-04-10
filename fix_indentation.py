#!/usr/bin/env python
# Script to fix indentation issues in views.py

import re

with open('myapp/views.py', 'r') as f:
    lines = f.readlines()

# Fix for get_notification_count (around line 955)
for i in range(len(lines)):
    if 'def get_notification_count' in lines[i]:
        # Fix the indentation for the next few lines
        start_index = i + 1
        lines[start_index] = '    """API endpoint to get the number of unread notifications for a user"""\n'
        lines[start_index+1] = '    if request.user.is_authenticated:\n'
        lines[start_index+2] = '        count = UserNotification.objects.filter(user=request.user, is_read=False).count()\n'
        lines[start_index+3] = '        return JsonResponse({\'count\': count})\n'
        lines[start_index+4] = '    return JsonResponse({\'count\': 0})\n'
        break

# Fix for rto_modification_requests (around line 1045)
for i in range(len(lines)):
    if '# Filter requests based on RTO jurisdiction' in lines[i] and '# Get vehicles with registration numbers' in lines[i+1]:
        # Find and fix the indentation for these lines
        lines[i+2] = '    requests = VehicleModificationRequest.objects.filter(\n'
        lines[i+3] = '        vehicle__registration_number__startswith=f"KL {rto_reg_number}"\n'
        lines[i+4] = '    ).order_by(\'-created_at\')\n'
        break

# Write the fixed content back to the file
with open('myapp/views.py', 'w') as f:
    f.writelines(lines)

print("Indentation issues fixed in views.py")

def fix_impose_fine_indentation():
    try:
        with open('myapp/views.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the impose_fine function
        impose_fine_pattern = r'@login_required\s*?\ndef impose_fine\(request\):.*?def rto_fine_list\(request\):'
        impose_fine_match = re.search(impose_fine_pattern, content, re.DOTALL)
        
        if not impose_fine_match:
            print("Could not find the impose_fine function in views.py")
            return False
        
        # Get the function code
        function_code = impose_fine_match.group(0)
        
        # Fix the indentation issues
        fixed_function_code = '''@login_required
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

def rto_fine_list(request):'''
        
        # Replace the function in the content
        fixed_content = content.replace(function_code, fixed_function_code)
        
        # Write back to file
        with open('myapp/views.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("Successfully fixed indentation in impose_fine function")
        return True
    except Exception as e:
        print(f"Error fixing indentation: {str(e)}")
        return False

if __name__ == "__main__":
    fix_impose_fine_indentation() 