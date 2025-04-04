import re

# Read the content of views.py
try:
    with open('myapp/views.py', 'r', encoding='utf-8') as file:
        content = file.read()
except:
    # Try with a different encoding if needed
    with open('myapp/views.py', 'r') as file:
        content = file.read()

# Fix the impose_fine function indentation issues
corrected_impose_fine = '''@login_required
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
    
    return render(request, 'impose_fine.html', context)'''

# Fix the get_notification_count function indentation issues
corrected_get_notification_count = '''def get_notification_count(request):
    """API endpoint to get the number of unread notifications for a user"""
    if request.user.is_authenticated:
        count = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})'''

# Fix the rto_modification_requests function indentation issues
corrected_rto_modification_requests = '''@login_required
def rto_modification_requests(request):
    """View for RTO officers to see all modification requests"""
    if not request.user.user_type == 'RTO':
        messages.error(request, "Access denied. Only RTO users can access this page.")
        return redirect('home')
    
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    
    # Get RTO's registration code (e.g., '06' from 'KL 06')
    rto_reg_number = request.user.reg_number
    
    requests = []
    rto_jurisdiction = "Not configured"
    
    if not rto_reg_number:
        messages.warning(request, "Your RTO registration number is not configured. Please contact admin to set up your jurisdiction.")
    else:
        # Filter requests based on RTO jurisdiction
        # Get vehicles with registration numbers starting with the RTO's code
        requests = VehicleModificationRequest.objects.filter(
            vehicle__registration_number__startswith=f"KL {rto_reg_number}"
        ).order_by('-created_at')
        
        if status_filter:
            requests = requests.filter(status=status_filter)
        
        if type_filter:
            requests = requests.filter(request_type=type_filter)
            
        rto_jurisdiction = f"KL {rto_reg_number}"
    
    return render(request, 'rto_modification_requests.html', {
        'requests': requests,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'request_types': VehicleModificationRequest.REQUEST_TYPES,
        'status_choices': VehicleModificationRequest.STATUS_CHOICES,
        'rto_jurisdiction': rto_jurisdiction
    })'''

# Replace the impose_fine function
impose_fine_pattern = r'@login_required\s+def\s+impose_fine\(request\):.*?def\s+rto_fine_list\('
match = re.search(impose_fine_pattern, content, re.DOTALL)
if match:
    start_pos = match.start()
    end_pos = match.end() - len('def rto_fine_list(')
    new_content = content[:start_pos] + corrected_impose_fine + "\n\n" + content[end_pos:]
    content = new_content

# Replace the get_notification_count function
get_notification_count_pattern = r'def\s+get_notification_count\(request\):.*?@login_required'
match = re.search(get_notification_count_pattern, content, re.DOTALL)
if match:
    start_pos = match.start()
    end_pos = match.end() - len('@login_required')
    new_content = content[:start_pos] + corrected_get_notification_count + "\n\n" + content[end_pos:]
    content = new_content

# Replace the rto_modification_requests function
rto_modification_requests_pattern = r'@login_required\s+def\s+rto_modification_requests\(request\):.*?@login_required\s+def\s+rto_modification_request_detail\('
match = re.search(rto_modification_requests_pattern, content, re.DOTALL)
if match:
    start_pos = match.start()
    end_pos = match.end() - len('@login_required\ndef rto_modification_request_detail(')
    new_content = content[:start_pos] + corrected_rto_modification_requests + "\n\n" + content[end_pos:]
    content = new_content

# Write the fixed content back to the file
with open('myapp/views.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("Successfully fixed all indentation issues in views.py") 