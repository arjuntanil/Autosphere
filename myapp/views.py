from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.utils.timezone import now
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404, HttpResponseBadRequest, HttpResponse
import re
import os
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.urls import reverse
import razorpay
import time
from django.views.decorators.csrf import csrf_exempt
import json
import hmac
import hashlib
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from io import BytesIO
from datetime import datetime
from django.db import transaction

from .models import CustomUser, Vehicle, Notice, PersonalizedVehicle, VehicleFine, UserNotification, VehicleModificationRequest, PasswordResetVerification, FinePayment, ViolationDocument
from .forms import CustomUserCreationForm, VehicleRegistrationForm, NoticeForm, VehicleVerificationForm, VehicleFineForm, FineForm, VehicleModificationRequestForm, ModificationRequestUpdateForm, PasswordResetRequestForm, VerificationCodeForm, PasswordResetForm
from django.utils import timezone

User = get_user_model()

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.user_type == 'RTO':
                return redirect('rto_home')
            return redirect('home')
        else:
            # Add error context to pass to the template
            return render(request, 'login.html', {'error': True, 'form_data': {'username': username}})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if user.user_type == 'RTO':
                return redirect('rto_home')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def home(request):
    """View for user dashboard home page"""
    if request.user.is_rto:
        return redirect('rto_home')
    
    # Check for any persistent success message in session
    update_message = None
    if 'vehicle_updated' in request.session:
        vehicle_data = request.session.pop('vehicle_updated')
        update_message = f"Vehicle {vehicle_data['registration_number']} details updated successfully."
    
    # Get user's personalized vehicles
    personalized_vehicles = PersonalizedVehicle.objects.filter(user=request.user).select_related('vehicle')
    
    # Get upcoming expiry dates
    today = timezone.now().date()
    expiry_warning_days = 30  # Show warning for documents expiring within 30 days
    
    for vehicle in personalized_vehicles:
        # Check registration validity date
        vehicle.reg_expiring_soon = False
        if vehicle.vehicle.registration_validity_date:
            days_to_reg_expiry = (vehicle.vehicle.registration_validity_date - today).days
            vehicle.reg_expiring_soon = 0 < days_to_reg_expiry <= expiry_warning_days
            vehicle.days_to_reg_expiry = days_to_reg_expiry
        
        # Check PUC validity date
        vehicle.puc_expiring_soon = False
        if vehicle.vehicle.puc_validity_date:
            days_to_puc_expiry = (vehicle.vehicle.puc_validity_date - today).days
            vehicle.puc_expiring_soon = 0 < days_to_puc_expiry <= expiry_warning_days
            vehicle.days_to_puc_expiry = days_to_puc_expiry
    
    # Get user's unpaid fines
    unpaid_fines = VehicleFine.objects.filter(
        vehicle__in=[pv.vehicle for pv in personalized_vehicles],
        payment_status='Unpaid'
    ).order_by('due_date')
    
    # Get recent notices
    now = timezone.now()
    recent_notices = Notice.objects.filter(
        Q(is_active=True) & (Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    ).order_by('-created_at')[:5]
    
    context = {
        'personalized_vehicles': personalized_vehicles,
        'unpaid_fines': unpaid_fines,
        'recent_notices': recent_notices,
        'today': today,
        'update_message': update_message
    }
    
    return render(request, 'home.html', context)

def search_vehicle_by_registration(registration_number):
    """
    Advanced search function for normal users to find a vehicle by registration number.
    Analyzes the pattern like "KL 06 0001" to find the corresponding vehicle.
    """
    if not registration_number:
        return None
    
    # Clean and normalize the input
    clean_input = registration_number.upper().strip()
    
    # Try direct match first
    try:
        return Vehicle.objects.get(registration_number__iexact=clean_input)
    except Vehicle.DoesNotExist:
        pass
    
    # Remove all spaces for pattern matching
    no_space_input = ''.join(clean_input.split())
    
    # Try to match the pattern: KL 06 0001 (state code, RTO code, sequence number)
    pattern = re.match(r"([A-Z]{2})(\d{2})([A-Z]?)(\d+)", no_space_input)
    
    if pattern:
        state, rto_code, letter, number = pattern.groups()
        
        # Ensure number is padded to 4 digits for comparison
        try:
            if len(number) <= 4:
                formatted_number = f"{int(number):04d}"
            else:
                # If longer than 4 digits but starts with zeros, keep original
                if number.startswith('0'):
                    formatted_number = number
                else:
                    # For long numbers, try to extract actual number part
                    formatted_number = f"{int(number):04d}"
        except ValueError:
            formatted_number = number
            
        if letter:
            formatted_reg = f"{state} {rto_code} {letter} {formatted_number}"
        else:
            formatted_reg = f"{state} {rto_code} {formatted_number}"
        
        # Try to find the vehicle with the formatted registration number
        try:
            return Vehicle.objects.get(registration_number__iexact=formatted_reg)
        except Vehicle.DoesNotExist:
            # If not found, try with a more flexible approach
            vehicles = Vehicle.objects.filter(registration_number__istartswith=f"{state} {rto_code}")
            
            for vehicle in vehicles:
                # Clean both registration numbers for comparison
                clean_vehicle_reg = ''.join(vehicle.registration_number.upper().split())
                
                if no_space_input == clean_vehicle_reg:
                    return vehicle
                
                # Check if the number part matches
                vehicle_pattern = re.match(r"([A-Z]{2})(\d{2})([A-Z]?)(\d+)", clean_vehicle_reg)
                if vehicle_pattern:
                    v_state, v_rto, v_letter, v_number = vehicle_pattern.groups()
                    
                    # If state and RTO code match, check if number matches (ignoring leading zeros)
                    if state == v_state and rto_code == v_rto:
                        if int(number) == int(v_number):
                            return vehicle
    
    # If no match found, return None
    return None

@login_required
def rto_home(request):
    """Home page for RTO officials"""
    if not request.user.is_rto:
        messages.error(request, "You don't have permission to access the RTO dashboard.")
        return redirect('home')
        
    # Check for any persistent success message in session
    update_message = None
    if 'vehicle_updated' in request.session:
        vehicle_data = request.session.pop('vehicle_updated')
        update_message = f"Vehicle {vehicle_data['registration_number']} details updated successfully."
    
    # Get statistics
    total_vehicles = Vehicle.objects.count()
    blacklisted_vehicles = Vehicle.objects.filter(blacklist_status=True).count()
    total_fines = VehicleFine.objects.filter(imposed_by=request.user).count()
    unpaid_fines = VehicleFine.objects.filter(imposed_by=request.user, payment_status='Unpaid').count()
    
    # Get recent vehicles
    recent_vehicles = Vehicle.objects.all().order_by('-registered_at')[:5]
    
    # Get RTO's registration code (e.g., '06' from 'KL 06')
    rto_reg_number = request.user.reg_number
    
    # Get recent pending modification requests for this RTO's jurisdiction
    recent_requests = []
    if rto_reg_number:
        recent_requests = VehicleModificationRequest.objects.filter(
            vehicle__registration_number__startswith=f"KL {rto_reg_number}",
            status='pending'
        ).order_by('-created_at')[:5]
    
    # Get jurisdiction label
    rto_jurisdiction = f"KL {rto_reg_number}" if rto_reg_number else "Not configured"
    
    return render(request, 'rto_home.html', {
        'total_vehicles': total_vehicles,
        'blacklisted_vehicles': blacklisted_vehicles,
        'total_fines': total_fines,
        'unpaid_fines': unpaid_fines,
        'recent_vehicles': recent_vehicles,
        'recent_requests': recent_requests,
        'rto_jurisdiction': rto_jurisdiction,
        'update_message': update_message
    })

def generate_next_registration_number(rto_reg_number):
    """
    Generates the next available vehicle registration number.
    
    The system will:
    1. Find the first available number in the range 0001-9999
    2. If all numbers 0001-9999 are taken, move to A 0001-A 9999
    3. Continue with B, C, etc. until Z, then AA, AB, etc.
    4. Always verify the registration number is unique
    """
    # Base prefix for all registration numbers with this RTO code
    prefix = f"KL {rto_reg_number}"
    
    # Step 1: Check for numeric-only registration numbers (0001-9999)
    existing_numeric = set()
    
    # Get all vehicles with numeric-only registration numbers
    numeric_vehicles = Vehicle.objects.filter(
        registration_number__startswith=prefix,
        registration_number__regex=r'^KL \d{2} \d{4}$'
    )
    
    # Add all existing numeric registration numbers to the set
    for vehicle in numeric_vehicles:
        reg_parts = vehicle.registration_number.split()
        if len(reg_parts) == 3:  # Format: KL XX YYYY
            try:
                num = int(reg_parts[2])
                existing_numeric.add(num)
            except ValueError:
                pass
    
    # Find the first available number in range 0001-9999
    for num in range(1, 10000):
        if num not in existing_numeric:
            return f"{prefix} {num:04d}"
    
    # Step 2: All numeric slots are taken, check alphabetic series
    # Start from A and go up to Z
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        # Get all registration numbers for this letter series
        letter_vehicles = Vehicle.objects.filter(
            registration_number__startswith=f"{prefix} {letter}"
        )
        
        # Create a set of existing numbers for this letter
        existing_letter_nums = set()
        for vehicle in letter_vehicles:
            reg_parts = vehicle.registration_number.split()
            if len(reg_parts) == 4:  # Format: KL XX A YYYY
                try:
                    num = int(reg_parts[3])
                    existing_letter_nums.add(num)
                except ValueError:
                    pass
        
        # Find the first available number in this letter series
        for num in range(1, 10000):
            if num not in existing_letter_nums:
                return f"{prefix} {letter} {num:04d}"
    
    # Step 3: If code reaches here, we need to go to AA, AB, etc.
    # This is very unlikely but we'll implement it for completeness
    for first_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for second_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            double_letter = f"{first_letter}{second_letter}"
            letter_vehicles = Vehicle.objects.filter(
                registration_number__startswith=f"{prefix} {double_letter}"
            )
            
            # Create a set of existing numbers for this double letter
            existing_letter_nums = set()
            for vehicle in letter_vehicles:
                reg_parts = vehicle.registration_number.split()
                if len(reg_parts) == 4:  # Format: KL XX AA YYYY
                    try:
                        num = int(reg_parts[3])
                        existing_letter_nums.add(num)
                    except ValueError:
                        pass
            
            # Find the first available number in this double letter series
            for num in range(1, 10000):
                if num not in existing_letter_nums:
                    return f"{prefix} {double_letter} {num:04d}"
    
    # Fallback (extremely unlikely to reach here)
    return f"{prefix} AAA 0001"

@login_required
def register_vehicle(request):
    if request.user.user_type != 'RTO':
        return redirect('home')

    if request.method == 'POST':
        form = VehicleRegistrationForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            
            # Handle registration number
            if form.cleaned_data.get('use_manual_entry'):
                # For manual entry, format the number with RTO code
                reg_number = form.cleaned_data['registration_number']
                vehicle.registration_number = f"KL {request.user.reg_number} {reg_number}"
            else:
                # Auto-generate registration number
                vehicle.registration_number = generate_next_registration_number(request.user.reg_number)
            
            # Set location and registered_by fields
            vehicle.location = request.user.location
            vehicle.registered_by = request.user
            
            vehicle.save()
            messages.success(request, 'Vehicle registered successfully!')
            return redirect('rto_home')
    else:
        auto_registration_number = generate_next_registration_number(request.user.reg_number)
        form = VehicleRegistrationForm(initial={'registration_number': auto_registration_number})

    return render(request, 'register_vehicle.html', {'form': form})

def normalize_registration_number(query):
    """
    Normalizes user input to match stored registration number format.
    Example:
        "kl06a0001"  -> "KL 06 A 0001"
        "kl06 01"    -> "KL 06 0001"
        "kl061"      -> "KL 06 0001"
        "kl060001"   -> "KL 06 0001"
        "KL06001"    -> "KL 06 0001"
        "KL 06 001"  -> "KL 06 0001"
    """
    # Remove spaces and convert to uppercase
    clean_query = query.upper().replace(" ", "")
    
    # Basic pattern match for state+district+number
    match = re.match(r"([A-Z]{2})(\d{2})([A-Z]?)(\d+)", clean_query)
    
    if match:
        state, district, letter, number = match.groups()
        
        # Ensure number is padded to 4 digits for comparison
        try:
            if len(number) <= 4:
                formatted_number = f"{int(number):04d}"
            else:
                # If longer than 4 digits but starts with zeros, keep original
                if number.startswith('0'):
                    formatted_number = number
                else:
                    # For long numbers, try to extract actual number part
                    formatted_number = f"{int(number):04d}"
        except ValueError:
            formatted_number = number
            
        if letter:
            return f"{state} {district} {letter} {formatted_number}"
        return f"{state} {district} {formatted_number}"
    
    return query

@login_required
def search_vehicle(request):
    query = request.GET.get('q', '')
    vehicles = []
    search_error = None
    
    if query and len(query.strip()) > 0:
        # For normal users, use the optimized search function
        if not request.user.user_type == 'RTO':
            vehicle = search_vehicle_by_registration(query)
            if vehicle:
                vehicles = [vehicle]
            else:
                search_error = "No vehicle found with this registration number."
        else:
            # RTO user search - keep the existing implementation
            # Clean the query - remove spaces and convert to uppercase
            clean_query = ''.join(query.strip().upper().split())
            
            # Try to match the exact vehicle first
            all_vehicles = Vehicle.objects.all()
            exact_match = None
            
            for vehicle in all_vehicles:
                # Clean the registration number for comparison
                clean_reg = ''.join(vehicle.registration_number.upper().split())
                
                # Check for exact match (ignoring spaces)
                if clean_query == clean_reg:
                    exact_match = vehicle
                    break
            
            if exact_match:
                # If we found an exact match, return only that vehicle
                vehicles = [exact_match]
            else:
                # For partial searches, still maintain original flexible search
                for vehicle in all_vehicles:
                    # Clean the registration number for comparison
                    clean_reg = ''.join(vehicle.registration_number.upper().split())
                    
                    # Match if the cleaned query is present in the registration number
                    if clean_query in clean_reg:
                        vehicles.append(vehicle)
                
                # Also try to match by owner name or chassis number
                more_vehicles = Vehicle.objects.filter(
                    Q(owner_name__icontains=query) |
                    Q(chassis_number__icontains=query)
                ).exclude(id__in=[v.id for v in vehicles])
                
                vehicles.extend(more_vehicles)
    
    # Check if each vehicle is already personalized by the current user
    if request.user.is_authenticated and vehicles:
        # Get all personalized vehicles for the current user
        personalized_vehicle_ids = PersonalizedVehicle.objects.filter(
            user=request.user
        ).values_list('vehicle_id', flat=True)
        
        # Set is_personalized flag for each vehicle
        for vehicle in vehicles:
            vehicle.is_personalized = vehicle.id in personalized_vehicle_ids
    
    context = {
        'vehicles': vehicles,
        'query': query,
        'search_error': search_error,
        'is_rto': request.user.user_type == 'RTO' if hasattr(request.user, 'user_type') else False
    }
    
    if hasattr(request.user, 'user_type') and request.user.user_type == 'RTO':
        # Use a different template for RTO users that shows more details and actions
        return render(request, 'rto_vehicle_search.html', context)
    else:
        return render(request, 'search_results.html', context)

# Notice views for all users
def notice_list(request):
    """View to display all active notices for all users"""
    now = timezone.now()
    notices = Notice.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now),
        is_active=True
    ).order_by('-created_at')
    return render(request, 'notice_list.html', {'notices': notices})

def notice_detail(request, notice_id):
    """View to display details of a specific notice"""
    notice = get_object_or_404(Notice, id=notice_id)
    return render(request, 'notice_detail.html', {'notice': notice})

# Notice views for RTO users
@login_required
@user_passes_test(lambda u: u.user_type == 'RTO')
def rto_notice_list(request):
    """View to display notices created by the logged-in RTO user"""
    notices = Notice.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'rto_notice_list.html', {'notices': notices})

@login_required
@user_passes_test(lambda u: u.user_type == 'RTO')
def create_notice(request):
    """View to create a new notice"""
    if request.method == 'POST':
        form = NoticeForm(request.POST)
        if form.is_valid():
            notice = form.save(commit=False)
            notice.created_by = request.user
            
            # Handle expiry date - only save if has_expiry checkbox was checked
            has_expiry = request.POST.get('has_expiry')
            if not has_expiry:
                notice.expires_at = None
                
            notice.save()
            
            # Create notifications for all users about the new notice
            UserNotification.create_notice_notification(notice)
            
            return redirect('rto_notice_list')
    else:
        form = NoticeForm()
    
    return render(request, 'create_notice.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.user_type == 'RTO')
def edit_notice(request, notice_id):
    """View to edit an existing notice"""
    notice = get_object_or_404(Notice, id=notice_id, created_by=request.user)
    
    if request.method == 'POST':
        form = NoticeForm(request.POST, instance=notice)
        if form.is_valid():
            notice = form.save(commit=False)
            
            # Handle expiry date - only save if has_expiry checkbox was checked
            has_expiry = request.POST.get('has_expiry')
            if not has_expiry:
                notice.expires_at = None
                
            notice.save()
            return redirect('notice_detail', notice_id=notice.id)
    else:
        form = NoticeForm(instance=notice)
    
    return render(request, 'edit_notice.html', {'form': form, 'notice': notice})

@login_required
@user_passes_test(lambda u: u.user_type == 'RTO')
def delete_notice(request, notice_id):
    """View to delete a notice"""
    notice = get_object_or_404(Notice, id=notice_id, created_by=request.user)
    
    if request.method == 'POST':
        notice.delete()
        return redirect('rto_notice_list')
    
    return render(request, 'delete_notice.html', {'notice': notice})

# Vehicle personalization views
@login_required
def personalized_vehicles(request):
    """Display user's personalized vehicles"""
    today = timezone.now().date()
    
    # Check for any persistent success message in session
    update_message = None
    if 'vehicle_updated' in request.session:
        vehicle_data = request.session.pop('vehicle_updated')
        update_message = f"Vehicle {vehicle_data['registration_number']} details updated successfully."
    
    # Get user's personalized vehicles with related vehicle data
    vehicles = PersonalizedVehicle.objects.filter(user=request.user).select_related('vehicle')
    
    # Add fine counts and document expiry status to each personalized vehicle
    for vehicle in vehicles:
        # Count unpaid fines
        vehicle.unpaid_fines_count = VehicleFine.objects.filter(
            vehicle=vehicle.vehicle, 
            payment_status='Unpaid'
        ).count()
        
        # Check document expiry status
        vehicle.has_expired_registration = False
        vehicle.has_expired_puc = False
        
        # Check registration validity
        if vehicle.vehicle.registration_validity_date:
            vehicle.has_expired_registration = vehicle.vehicle.registration_validity_date < today
            vehicle.days_to_registration_expiry = (vehicle.vehicle.registration_validity_date - today).days
            if vehicle.has_expired_registration:
                vehicle.days_since_registration_expiry = abs(vehicle.days_to_registration_expiry)
        
        # Check PUC validity
        if vehicle.vehicle.puc_validity_date:
            vehicle.has_expired_puc = vehicle.vehicle.puc_validity_date < today
            vehicle.days_to_puc_expiry = (vehicle.vehicle.puc_validity_date - today).days
            if vehicle.has_expired_puc:
                vehicle.days_since_puc_expiry = abs(vehicle.days_to_puc_expiry)
        
        # Combined expiry status for template
        vehicle.has_expired_documents = vehicle.has_expired_registration or vehicle.has_expired_puc
    
    return render(request, 'personalized_vehicles.html', {
        'vehicles': vehicles,
        'today': today,
        'update_message': update_message
    })

@login_required
def personalize_vehicle(request, registration_number):
    """View to personalize a vehicle after verification"""
    vehicle = get_object_or_404(Vehicle, registration_number=registration_number)
    
    # Check if the vehicle is already personalized by this user
    existing = PersonalizedVehicle.objects.filter(user=request.user, vehicle=vehicle).first()
    if existing:
        messages.info(request, f"This vehicle is already in your personalized list as '{existing}'")
        return redirect('personalized_vehicles')
    
    if request.method == 'POST':
        form = VehicleVerificationForm(request.POST, vehicle=vehicle)
        if form.is_valid():
            # Create the personalized vehicle entry
            is_first = not PersonalizedVehicle.objects.filter(user=request.user).exists()
            personalized = PersonalizedVehicle.objects.create(
                user=request.user,
                vehicle=vehicle,
                nickname=form.cleaned_data.get('nickname'),
                is_primary=is_first  # First vehicle becomes primary by default
            )
            messages.success(request, f"Vehicle {vehicle.registration_number} has been added to your personalized vehicles.")
            return redirect('personalized_vehicles')
    else:
        form = VehicleVerificationForm(vehicle=vehicle)
    
    return render(request, 'personalize_vehicle.html', {'form': form, 'vehicle': vehicle})

@login_required
def set_primary_vehicle(request, id):
    """Set a personalized vehicle as primary"""
    vehicle = get_object_or_404(PersonalizedVehicle, id=id, user=request.user)
    vehicle.is_primary = True
    vehicle.save()
    messages.success(request, f"{vehicle} has been set as your primary vehicle")
    return redirect('personalized_vehicles')

@login_required
def remove_personalized_vehicle(request, id):
    """Remove a vehicle from personalized list"""
    vehicle = get_object_or_404(PersonalizedVehicle, id=id, user=request.user)
    
    if request.method == 'POST':
        vehicle_name = str(vehicle)
        vehicle.delete()
        messages.success(request, f"{vehicle_name} has been removed from your personalized vehicles")
        return redirect('personalized_vehicles')
    
    return render(request, 'remove_personalized_vehicle.html', {'vehicle': vehicle})

# Vehicle Fine related views
@login_required
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

@login_required
def rto_fine_list(request):
    """View for RTO users to see all fines"""
    if not request.user.user_type == 'RTO':
        messages.error(request, "You do not have permission to view RTO fines")
        return redirect('home')
    
    # Initialize queryset - filter by currently logged-in RTO user
    fines = VehicleFine.objects.filter(imposed_by=request.user).order_by('-imposed_date')
    
    # Apply filters based on GET parameters
    vehicle_number = request.GET.get('vehicle_number', '')
    vehicle_id = request.GET.get('vehicle_id', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    status = request.GET.get('status', '')
    
    # Filter by vehicle ID (takes precedence over registration number)
    if vehicle_id:
        try:
            vehicle_id = int(vehicle_id)
            fines = fines.filter(vehicle_id=vehicle_id)
        except (ValueError, TypeError):
            pass
    # Filter by vehicle registration number
    elif vehicle_number:
        normalized_number = normalize_registration_number(vehicle_number)
        fines = fines.filter(
            Q(vehicle__registration_number__icontains=vehicle_number) |
            Q(vehicle__registration_number__icontains=normalized_number)
        )
    
    # Filter by amount
    if min_amount:
        try:
            min_amount = float(min_amount)
            fines = fines.filter(fine_amount__gte=min_amount)
        except (ValueError, TypeError):
            pass
    
    if max_amount:
        try:
            max_amount = float(max_amount)
            fines = fines.filter(fine_amount__lte=max_amount)
        except (ValueError, TypeError):
            pass
    
    # Filter by date
    if from_date:
        try:
            from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').date()
            fines = fines.filter(imposed_date__date__gte=from_date_obj)
        except (ValueError, TypeError):
            pass
    
    if to_date:
        try:
            to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').date()
            fines = fines.filter(imposed_date__date__lte=to_date_obj)
        except (ValueError, TypeError):
            pass
    
    # Filter by status
    if status:
        fines = fines.filter(payment_status=status)
    
    return render(request, 'rto_fine_list.html', {
        'fines': fines,
        'status_choices': VehicleFine.PAYMENT_STATUS
    })

@login_required
def rto_fine_details(request, fine_id):
    """View for RTO users to see details of a specific fine they imposed"""
    if not request.user.user_type == 'RTO':
        messages.error(request, "You do not have permission to view fine details")
        return redirect('home')
    
    try:
        # Only allow viewing fines imposed by the current RTO user
        fine = VehicleFine.objects.get(id=fine_id, imposed_by=request.user)
        
        context = {
            'fine': fine,
            'is_rto': True,  # Flag to customize the template for RTO users
        }
        
        # Add document information if available
        if fine.violation_document:
            context['document_type'] = fine.get_document_type()
            
        # Get payment information if available
        if fine.payment_status == 'Paid':
            payment = fine.get_latest_payment_attempt()
            if payment:
                context['payment'] = payment
        
        return render(request, 'fine_details.html', context)
    except VehicleFine.DoesNotExist:
        messages.error(request, "Fine not found or you don't have permission to view it.")
        return redirect('rto_fine_list')

@login_required
def update_fine_status(request, fine_id):
    """View for RTO users to update fine status"""
    if not request.user.user_type == 'RTO':
        messages.error(request, "You do not have permission to update fines")
        return redirect('home')
    
    fine = get_object_or_404(VehicleFine, pk=fine_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(VehicleFine.PAYMENT_STATUS):
            fine.payment_status = new_status
            if new_status == 'Paid':
                fine.payment_date = timezone.now()
            fine.save()
            messages.success(request, f"Fine status updated to {new_status}")
        else:
            messages.error(request, "Invalid status")
        
        return redirect('rto_fine_list')
    
    return render(request, 'update_fine_status.html', {
        'fine': fine,
        'statuses': VehicleFine.PAYMENT_STATUS
    })

@login_required
def delete_fine(request, fine_id):
    """View for RTO users to delete a fine"""
    if not request.user.user_type == 'RTO':
        messages.error(request, "You do not have permission to delete fines")
        return redirect('home')
    
    fine = get_object_or_404(VehicleFine, pk=fine_id)
    
    if request.method == 'POST':
        reg_number = fine.vehicle.registration_number
        fine.delete()
        messages.success(request, f"Fine for vehicle {reg_number} deleted successfully")
        return redirect('rto_fine_list')
    
    return render(request, 'delete_fine.html', {
        'fine': fine
    })

@login_required
def user_vehicle_fines(request):
    # Get all personalized vehicles for the user
    personalized_vehicles = PersonalizedVehicle.objects.filter(user=request.user)
    
    # Get all vehicle registration numbers
    registration_numbers = [pv.vehicle.registration_number for pv in personalized_vehicles]
    
    # Get all fines for these vehicles
    fines = VehicleFine.objects.filter(vehicle__registration_number__in=registration_numbers).order_by('-imposed_date')
    
    # Count of unpaid fines
    unpaid_fines_count = fines.filter(payment_status='Unpaid').count()
    
    return render(request, 'user_vehicle_fines.html', {
        'fines': fines,
        'unpaid_fines_count': unpaid_fines_count,
    })

@login_required
def fine_details(request, fine_id):
    try:
        fine = VehicleFine.objects.get(id=fine_id)
        # Check if the user owns this vehicle
        if not PersonalizedVehicle.objects.filter(user=request.user, vehicle=fine.vehicle).exists():
            messages.error(request, "You do not have permission to view this fine.")
            return redirect('user_vehicle_fines')
        
        context = {
            'fine': fine,
        }
        
        # Add document information if available
        if fine.violation_document:
            context['document_type'] = fine.get_document_type()
            
        return render(request, 'fine_details.html', context)
    except VehicleFine.DoesNotExist:
        messages.error(request, "Fine not found.")
        return redirect('user_vehicle_fines')

@login_required
def rto_vehicle_search(request):
    if not request.user.user_type == 'RTO':
        messages.error(request, 'Access denied. Only RTO users can access this page.')
        return redirect('home')
    
    query = request.GET.get('q', '')
    vehicles = []
    
    if query:
        # Try to find exact matches first using normalization
        if len(query.strip()) >= 3:  # Only normalize if query has at least 3 chars
            normalized_query = normalize_registration_number(query)
            
            # Get all vehicles and try to match exactly
            all_vehicles = Vehicle.objects.all()
            exact_matches = []
            
            for vehicle in all_vehicles:
                # Normalize the stored registration number
                normalized_reg = normalize_registration_number(vehicle.registration_number)
                
                # Compare with the normalized query
                if normalized_reg == normalized_query:
                    exact_matches.append(vehicle)
            
            # If we have exact matches, use only those
            if exact_matches:
                vehicles = exact_matches
            else:
                # Otherwise fall back to the broader search
                vehicles = Vehicle.objects.filter(
                    Q(registration_number__icontains=query) |
                    Q(chassis_number__icontains=query) |
                    Q(owner_name__icontains=query)
                ).order_by('-registered_at')
        else:
            # For very short queries, use the original search logic
            vehicles = Vehicle.objects.filter(
                Q(registration_number__icontains=query) |
                Q(chassis_number__icontains=query) |
                Q(owner_name__icontains=query)
            ).order_by('-registered_at')
        
        # For each vehicle, get fine details
        for vehicle in vehicles:
            # Get all fines associated with the vehicle
            all_fines = vehicle.fines.all()
            vehicle.total_fines = all_fines.count()
            
            # Only continue if vehicle has fines
            if vehicle.total_fines > 0:
                # Count fines by payment status
                vehicle.paid_fines = all_fines.filter(payment_status='Paid').count()
                vehicle.unpaid_fines = all_fines.filter(payment_status='Unpaid').count()
                vehicle.contested_fines = all_fines.filter(payment_status='Contested').count()
                vehicle.waived_fines = all_fines.filter(payment_status='Waived').count()
                vehicle.processing_fines = all_fines.filter(payment_status='Processing').count()
                
                # Calculate total fine amount (paid and unpaid)
                from django.db.models import Sum
                vehicle.total_fine_amount = all_fines.aggregate(Sum('fine_amount'))['fine_amount__sum'] or 0
                vehicle.unpaid_fine_amount = all_fines.filter(payment_status='Unpaid').aggregate(Sum('fine_amount'))['fine_amount__sum'] or 0
                
                # Get recent fines for display
                vehicle.recent_fines = all_fines.order_by('-imposed_date')[:3]
            else:
                # Set default values if vehicle has no fines
                vehicle.paid_fines = 0
                vehicle.unpaid_fines = 0
                vehicle.contested_fines = 0
                vehicle.waived_fines = 0
                vehicle.processing_fines = 0
                vehicle.total_fine_amount = 0
                vehicle.unpaid_fine_amount = 0
                vehicle.recent_fines = []
    
    context = {
        'vehicles': vehicles,
        'query': query,
    }
    return render(request, 'rto_vehicle_search.html', context)

@login_required
def edit_vehicle(request, vehicle_id):
    """View for RTO users to edit an existing vehicle's details"""
    if not request.user.user_type == 'RTO':
        messages.error(request, "You do not have permission to edit vehicle details.")
        return redirect('home')
    
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    
    if request.method == 'POST':
        form = VehicleRegistrationForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            
            # Store success message in session for persistence
            request.session['vehicle_updated'] = {
                'registration_number': vehicle.registration_number,
                'timestamp': str(timezone.now())
            }
            
            # Also set regular message for immediate display
            messages.success(request, f"Vehicle {vehicle.registration_number} details updated successfully.")
            
            # Notify users who have personalized this vehicle
            personalized_vehicles = PersonalizedVehicle.objects.filter(vehicle=vehicle)
            for pv in personalized_vehicles:
                UserNotification.objects.create(
                    user=pv.user,
                    notification_type='notice',
                    title="Vehicle Details Updated",
                    message=f"Your vehicle {vehicle.registration_number} details have been updated by an RTO official.",
                    related_vehicle=vehicle
                )
            
            next_url = request.GET.get('next', 'rto_home')
            return redirect(next_url)
    else:
        form = VehicleRegistrationForm(instance=vehicle)
    
    return render(request, 'edit_vehicle.html', {
        'form': form,
        'vehicle': vehicle
    })

# User Notification Views
@login_required
def user_notifications(request):
    """View to display all notifications for the current user"""
    # Get all notifications for the current user, ordered by creation date
    notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')
    
    # Count unread notifications
    unread_count = notifications.filter(is_read=False).count()
    
    return render(request, 'user_notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count
    })

@login_required
def notification_detail(request, notification_id):
    """View to display details of a specific notification and mark it as read"""
    notification = get_object_or_404(UserNotification, id=notification_id, user=request.user)
    
    # Mark notification as read if it's not already
    if not notification.is_read:
        notification.is_read = True
        notification.save()
    
    # Prepare context based on notification type
    context = {
        'notification': notification
    }
    
    # Add related objects to context if they exist
    if notification.related_vehicle:
        context['vehicle'] = notification.related_vehicle
    
    if notification.related_fine:
        context['fine'] = notification.related_fine
    
    if notification.related_notice:
        context['notice'] = notification.related_notice
    
    return render(request, 'notification_detail.html', context)

@login_required
def mark_all_notifications_read(request):
    """View to mark all notifications as read"""
    if request.method == 'POST':
        UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect('notifications')
    return redirect('notifications')
    
def get_notification_count(request):
    """API endpoint to get the number of unread notifications for a user"""
    if request.user.is_authenticated:
        count = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})

@login_required
def user_modification_requests(request):
    """View to display all modification requests for the current user"""
    requests = VehicleModificationRequest.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'user_modification_requests.html', {
        'requests': requests,
    })

@login_required
def create_modification_request(request, vehicle_id):
    """View for users to create a new modification request"""
    # Verify the vehicle is personalized by the user
    try:
        personalized_vehicle = PersonalizedVehicle.objects.get(
            user=request.user,
            vehicle_id=vehicle_id
        )
        vehicle = personalized_vehicle.vehicle
    except PersonalizedVehicle.DoesNotExist:
        messages.error(request, "You can only request modifications for vehicles you have personalized.")
        return redirect('personalized_vehicles')
    
    if request.method == 'POST':
        form = VehicleModificationRequestForm(request.POST, user=request.user, vehicle=vehicle)
        if form.is_valid():
            modification_request = form.save()
            messages.success(request, f"Your {modification_request.get_request_type_display()} request has been submitted.")
            
            # Create notification for RTO officers
            rto_users = CustomUser.objects.filter(user_type='RTO')
            for rto_user in rto_users:
                UserNotification.objects.create(
                    user=rto_user,
                    notification_type='notice',
                    title=f"New {modification_request.get_request_type_display()} Request",
                    message=f"A user has requested a {modification_request.get_request_type_display().lower()} for vehicle {vehicle.registration_number}.",
                    related_vehicle=vehicle
                )
            
            return redirect('user_modification_requests')
    else:
        form = VehicleModificationRequestForm(user=request.user, vehicle=vehicle)
    
    return render(request, 'create_modification_request.html', {
        'form': form,
        'vehicle': vehicle
    })

@login_required
def modification_request_detail(request, request_id):
    """View to display details of a specific modification request"""
    modification_request = get_object_or_404(
        VehicleModificationRequest, 
        id=request_id,
        user=request.user
    )
    
    return render(request, 'modification_request_detail.html', {
        'request': modification_request
    })

# RTO Officer Modification Request Views
@login_required
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
    })

@login_required
def rto_modification_request_detail(request, request_id):
    """View for RTO officers to review and update a modification request"""
    if not request.user.user_type == 'RTO':
        messages.error(request, "Access denied. Only RTO users can access this page.")
        return redirect('home')
    
    modification_request = get_object_or_404(VehicleModificationRequest, id=request_id)
    
    # Get RTO's registration code (e.g., '06' from 'KL 06')
    rto_reg_number = request.user.reg_number
    
    if not rto_reg_number:
        messages.warning(request, "Your RTO registration number is not configured. Please contact admin to set up your jurisdiction.")
    # Only check jurisdiction if the RTO has a registration number
    elif not modification_request.vehicle.registration_number.startswith(f"KL {rto_reg_number}"):
        messages.error(request, "Access denied. This vehicle is not under your jurisdiction.")
        return redirect('rto_modification_requests')
    
    if request.method == 'POST':
        form = ModificationRequestUpdateForm(request.POST, instance=modification_request)
        if form.is_valid():
            modified_request = form.save(commit=False)
            
            # If request is approved, update the vehicle details based on request type
            if modified_request.status == 'approved':
                vehicle = modification_request.vehicle
                
                if modification_request.request_type == 'ownership':
                    vehicle.owner_name = modification_request.requested_value
                elif modification_request.request_type == 'color':
                    vehicle.color = modification_request.requested_value
                elif modification_request.request_type == 'fuel':
                    vehicle.fuel_type = modification_request.requested_value
                
                vehicle.save()
                
                # Create notification for the user
                UserNotification.objects.create(
                    user=modification_request.user,
                    notification_type='notice',
                    title=f"Your {modification_request.get_request_type_display()} request was approved",
                    message=f"Your request to change {modification_request.get_request_type_display()} for vehicle {vehicle.registration_number} has been approved and processed.",
                    related_vehicle=vehicle
                )
            
            # If request is rejected, create a notification for the user
            elif modified_request.status == 'rejected':
                UserNotification.objects.create(
                    user=modification_request.user,
                    notification_type='notice',
                    title=f"Your {modification_request.get_request_type_display()} request was rejected",
                    message=f"Your request to change {modification_request.get_request_type_display()} for vehicle {modification_request.vehicle.registration_number} has been rejected. Reason: {modified_request.rto_comments or 'No reason provided'}",
                    related_vehicle=modification_request.vehicle
                )
            
            modified_request.save()
            messages.success(request, f"The {modification_request.get_request_type_display()} request has been updated.")
            return redirect('rto_modification_requests')
    else:
        form = ModificationRequestUpdateForm(instance=modification_request)
    
    return render(request, 'rto_modification_request_detail.html', {
        'form': form,
        'request': modification_request
    })

@login_required
def delete_modification_request(request, request_id):
    """View to allow users to delete their modification requests"""
    modification_request = get_object_or_404(
        VehicleModificationRequest, 
        id=request_id,
        user=request.user
    )
    
    # Only allow deletion of pending requests
    if modification_request.status != 'pending':
        messages.error(request, "Only pending requests can be deleted.")
        return redirect('modification_request_detail', request_id=request_id)
    
    if request.method == 'POST':
        # Get vehicle info for success message
        vehicle = modification_request.vehicle
        request_type = modification_request.get_request_type_display()
        
        # Delete the request
        modification_request.delete()
        
        messages.success(request, f"Your {request_type} request for vehicle {vehicle.registration_number} has been deleted.")
        return redirect('user_modification_requests')
    
    return render(request, 'delete_modification_request.html', {
        'request': modification_request
    })

@login_required
def serve_media_file(request, path):
    """
    Custom view to serve media files in development
    """
    import os
    from django.http import FileResponse, Http404, HttpResponse, JsonResponse
    from pathlib import Path
    from django.conf import settings
    import logging

    # Get logger
    logger = logging.getLogger(__name__)
    
    # Use settings.MEDIA_ROOT if available, otherwise define manually
    media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(Path(__file__).resolve().parent.parent, 'media'))
    
    # Handle the case when a FileField object is passed instead of a string
    # This happens when template uses {{ fine.violation_document }} instead of {{ fine.violation_document.name }}
    if hasattr(path, 'name'):
        path = path.name
    
    # Log the requested path for debugging
    logger.debug(f"Media file requested: {path}")
    
    # Normalize the path (handle both forward and backslashes)
    # Use the correct path separator for the operating system
    normalized_path = path.replace('/', os.path.sep).replace('\\', os.path.sep)
    
    # Build the absolute path to the requested file
    file_path = os.path.join(media_root, normalized_path)
    
    # Log the computed file path for debugging
    logger.debug(f"Computed file path: {file_path}")
    
    # Check if the request is asking for debug info
    if request.GET.get('debug', '0') == '1' and request.user.is_staff:
        debug_info = {
            'requested_path': path,
            'normalized_path': normalized_path,
            'file_path': file_path,
            'file_exists': os.path.exists(file_path),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'media_root': media_root,
            'file_name': os.path.basename(file_path),
            'directory': os.path.dirname(file_path),
            'directory_exists': os.path.exists(os.path.dirname(file_path)),
            'directory_contents': os.listdir(os.path.dirname(file_path)) if os.path.exists(os.path.dirname(file_path)) else []
        }
        return JsonResponse(debug_info)
    
    # Get the file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Check if the file exists
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        
        # Ensure directory exists for future uploads
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Raise a proper Http404 exception
        if file_ext == '.pdf':
            logger.error(f"PDF document not found: {file_path}")
            raise Http404("PDF document not found")
        else:
            # For images, create a placeholder
            try:
                # Generate a default "image not found" image
                from PIL import Image, ImageDraw, ImageFont
                
                img = Image.new('RGB', (400, 300), color='#f5f5f5')
                draw = ImageDraw.Draw(img)
                
                # Add message
                draw.text((20, 150), "Image not found", fill="#333333")
                draw.text((20, 180), f"Path: {path}", fill="#666666")
                
                # Create an in-memory file
                from io import BytesIO
                img_io = BytesIO()
                img.save(img_io, format='JPEG')
                img_io.seek(0)
                
                return FileResponse(img_io, content_type='image/jpeg')
            except Exception as e:
                logger.error(f"Error creating placeholder image: {str(e)}")
                raise Http404(f"File not found: {path}")
    
    try:
        # Log successful file access
        logger.debug(f"Successfully found file: {file_path}")
        
        # For PDF files, set the Content-Disposition header for proper downloading/viewing
        if file_ext == '.pdf':
            # Get the base name of the file (without directory path)
            filename = os.path.basename(file_path)
            
            # Open file in binary mode
            file_obj = open(file_path, 'rb')
            
            response = FileResponse(file_obj, content_type='application/pdf')
            
            # Handle inline viewing vs. attachment (download)
            is_download = request.GET.get('download', '0') == '1'
            if is_download:
                # For download, use attachment
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                logger.debug(f"Serving PDF as download: {filename}")
            else:
                # For inline viewing, use inline
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                logger.debug(f"Serving PDF inline: {filename}")
                
            return response
        else:
            # For other file types, use the standard FileResponse
            return FileResponse(open(file_path, 'rb'))
            
    except Exception as e:
        logger.error(f"Error serving file {file_path}: {str(e)}")
        raise Http404(f"Error accessing file: {str(e)}")

# Debug view for PDF files
@login_required
def debug_pdf_files(request):
    """
    Debug view to check PDF files in the system
    """
    import os
    from django.http import HttpResponse
    from pathlib import Path
    from django.conf import settings
    from .models import VehicleFine
    import glob
    
    # Get the media root directory
    media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(Path(__file__).resolve().parent.parent, 'media'))
    
    # Create or check the violation_documents directory
    violation_docs_dir = os.path.join(media_root, 'violation_documents')
    os.makedirs(violation_docs_dir, exist_ok=True)
    
    # Get all PDF files in the violation_documents directory
    pdf_files = glob.glob(os.path.join(violation_docs_dir, '*.pdf'))
    
    # Get all VehicleFine records with PDF documents
    fines_with_pdfs = VehicleFine.objects.exclude(violation_document='').exclude(violation_document__isnull=True)
    
    # Prepare the output
    output = []
    output.append("<h1>PDF Files Debug Information</h1>")
    
    # Check directories
    output.append("<h2>Directory Information</h2>")
    output.append(f"<p>Media Root: {media_root}</p>")
    output.append(f"<p>Media Root exists: {os.path.exists(media_root)}</p>")
    output.append(f"<p>Violation Documents directory: {violation_docs_dir}</p>")
    output.append(f"<p>Violation Documents directory exists: {os.path.exists(violation_docs_dir)}</p>")
    
    # List PDF files on disk
    output.append("<h2>PDF Files on Disk</h2>")
    if pdf_files:
        output.append("<ul>")
        for pdf_file in pdf_files:
            file_size = os.path.getsize(pdf_file)
            file_name = os.path.basename(pdf_file)
            output.append(f"<li>{file_name} ({file_size} bytes)</li>")
        output.append("</ul>")
    else:
        output.append("<p>No PDF files found on disk.</p>")
    
    # List Fine records with PDFs
    output.append("<h2>Vehicle Fines with PDF Documents</h2>")
    if fines_with_pdfs:
        output.append("<ul>")
        for fine in fines_with_pdfs:
            doc_path = fine.violation_document.name if fine.violation_document else "None"
            doc_url = f"/media/{doc_path}" if doc_path else "None"
            output.append(f"<li>Fine #{fine.id} - Document: {doc_path}</li>")
            output.append(f"<li style='margin-left: 20px;'>URL: <a href='{doc_url}' target='_blank'>{doc_url}</a></li>")
            
            # Check if the file exists on disk
            if fine.violation_document:
                full_path = os.path.join(media_root, doc_path)
                file_exists = os.path.exists(full_path)
                file_size = os.path.getsize(full_path) if file_exists else 0
                output.append(f"<li style='margin-left: 20px;'>File exists: {file_exists}, Size: {file_size} bytes</li>")
                
                # Add debug link
                debug_url = f"/media/{doc_path}/?debug=1"
                output.append(f"<li style='margin-left: 20px;'><a href='{debug_url}' target='_blank'>Debug Info</a></li>")
        output.append("</ul>")
    else:
        output.append("<p>No vehicle fines with PDF documents found in database.</p>")
    
    return HttpResponse("".join(output))

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(username=username, email=email)
                
                # Generate verification code
                verification = PasswordResetVerification.generate_code(user)
                
                # Send email
                subject = 'Password Reset Verification Code'
                message = f'Your verification code is: {verification.verification_code}\nThis code will expire in 15 minutes.'
                from_email = 'arjuntanil123@gmail.com'
                recipient_list = [email]
                
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=from_email,
                        recipient_list=recipient_list,
                        fail_silently=False,
                    )
                    # Store user_id in session for verification
                    request.session['reset_user_id'] = user.id
                    return redirect('verify_code')
                except Exception as e:
                    print(f"Email sending error: {str(e)}")  # Debug print
                    messages.error(request, f'Failed to send verification code: {str(e)}')
            except User.DoesNotExist:
                messages.error(request, 'User not found with the provided username and email.')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'forgot_password.html', {'form': form})

def verify_code(request):
    if 'reset_user_id' not in request.session:
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['verification_code']
            user_id = request.session['reset_user_id']
            
            try:
                verification = PasswordResetVerification.objects.get(
                    user_id=user_id,
                    verification_code=code,
                    is_used=False
                )
                
                if verification.is_valid():
                    verification.is_used = True
                    verification.save()
                    return redirect('reset_password')
                else:
                    messages.error(request, 'Verification code has expired. Please request a new one.')
            except PasswordResetVerification.DoesNotExist:
                messages.error(request, 'Invalid verification code. Please try again.')
    else:
        form = VerificationCodeForm()
    
    return render(request, 'verify_code.html', {'form': form})

def reset_password(request):
    if 'reset_user_id' not in request.session:
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if new_password1 != new_password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'reset_password.html')
            
        if len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'reset_password.html')
            
        if not any(char.isdigit() for char in new_password1):
            messages.error(request, 'Password must contain at least one number.')
            return render(request, 'reset_password.html')
        
        user_id = request.session['reset_user_id']
        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password1)
            user.save()
            messages.success(request, 'Password has been reset successfully. Please login with your new password.')
            del request.session['reset_user_id']
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'User not found. Please try again.')
    else:
        return render(request, 'reset_password.html')

@login_required
def profile(request):
    if request.method == 'POST':
        # Get the current user
        user = request.user
        
        # Get form data
        username = request.POST.get('username')
        phone_number = request.POST.get('phone_number')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Check if username is available (if changed)
        if username != user.username:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username is already taken.')
                return render(request, 'profile.html')
            user.username = username
        
        # Update other fields
        user.phone_number = phone_number
        user.first_name = first_name
        user.last_name = last_name
        
        # Handle password change if provided
        if new_password1 and new_password2:
            if new_password1 == new_password2:
                user.set_password(new_password1)
                messages.success(request, 'Password has been updated successfully.')
            else:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'profile.html')
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    return render(request, 'profile.html')

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.phone_number = request.POST.get('phone_number')
        user.date_of_birth = request.POST.get('date_of_birth')
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            # Delete old profile picture if it exists
            if user.profile_picture:
                import os
                from django.conf import settings
                old_picture_path = os.path.join(settings.MEDIA_ROOT, user.profile_picture.name)
                if os.path.isfile(old_picture_path):
                    os.remove(old_picture_path)
            
            # Save new profile picture
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    return render(request, 'edit_profile.html')

@login_required
def change_password(request):
    if request.method == 'POST':
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')
            
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')
            
        user.set_password(new_password)
        user.save()
        messages.success(request, 'Password changed successfully!')
        return redirect('profile')
        
    return render(request, 'change_password.html')

def pay_fine(request, fine_id):
    try:
        fine = VehicleFine.objects.get(id=fine_id)
        
        # Check if the user owns this vehicle
        if not PersonalizedVehicle.objects.filter(user=request.user, vehicle=fine.vehicle).exists():
            messages.error(request, "You do not have permission to pay this fine.")
            return redirect('user_vehicle_fines')
        
        # Check if fine is already paid
        if fine.payment_status == 'Paid':
            messages.info(request, "This fine has already been paid.")
            return redirect('fine_details', fine_id=fine_id)
        
        # Check if there's already a processing payment
        if fine.payment_status == 'Processing':
            existing_payment = fine.get_latest_payment_attempt()
            if existing_payment and existing_payment.status == 'created':
                # Use existing payment information
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                order = client.order.fetch(existing_payment.razorpay_order_id)
                
                return render(request, 'pay_fine.html', {
                    'fine': fine,
                    'order_id': existing_payment.razorpay_order_id,
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                    'callback_url': request.build_absolute_uri(reverse('payment_callback')),
                    'amount': int(fine.fine_amount * 100),  # Amount in paise
                    'currency': settings.RAZORPAY_CURRENCY,
                    'company_name': settings.RAZORPAY_COMPANY_NAME,
                    'description': settings.RAZORPAY_DESCRIPTION,
                    'company_logo': settings.RAZORPAY_COMPANY_LOGO,
                    'name': request.user.get_full_name() or request.user.username,
                    'email': request.user.email,
                    'contact': request.user.phone_number if hasattr(request.user, 'phone_number') else '',
                })
        
        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Create Razorpay order
        amount = int(fine.fine_amount * 100)  # Convert to paise
        receipt = f"fine_{fine.id}_{int(time.time())}"
        notes = {
            "fine_id": str(fine.id),
            "vehicle_number": fine.vehicle.registration_number,
            "violation_type": fine.violation_type,
            "user_id": str(request.user.id)
        }
        
        order_data = {
            'amount': amount,
            'currency': settings.RAZORPAY_CURRENCY,
            'receipt': receipt,
            'notes': notes,
        }
        
        order = client.order.create(data=order_data)
        
        # Create a payment record
        payment = FinePayment.objects.create(
            fine=fine,
            user=request.user,
            razorpay_order_id=order['id'],
            amount=fine.fine_amount,
            currency=settings.RAZORPAY_CURRENCY,
            receipt=receipt,
            status='created'
        )
        
        # Update fine status to Processing
        fine.payment_status = 'Processing'
        fine.razorpay_order_id = order['id']
        fine.save()
        
        return render(request, 'pay_fine.html', {
            'fine': fine,
            'order_id': order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'callback_url': request.build_absolute_uri(reverse('payment_callback')),
            'amount': amount,
            'currency': settings.RAZORPAY_CURRENCY,
            'company_name': settings.RAZORPAY_COMPANY_NAME,
            'description': settings.RAZORPAY_DESCRIPTION,
            'company_logo': settings.RAZORPAY_COMPANY_LOGO,
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'contact': request.user.phone_number if hasattr(request.user, 'phone_number') else '',
        })
        
    except VehicleFine.DoesNotExist:
        messages.error(request, "Fine not found.")
        return redirect('user_vehicle_fines')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('fine_details', fine_id=fine_id)

@csrf_exempt
def payment_callback(request):
    if request.method == "POST":
        try:
            # Get the payment details from the request
            payment_id = request.POST.get('razorpay_payment_id', '')
            order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Verify the payment signature
            params_dict = {
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': order_id,
                'razorpay_signature': signature
            }
            
            try:
                client.utility.verify_payment_signature(params_dict)
                # Signature verification successful
                
                # Find the payment record
                payment = FinePayment.objects.get(razorpay_order_id=order_id)
                payment_id = payment.id
                
                # Update payment status
                payment.razorpay_payment_id = payment_id
                payment.razorpay_signature = signature
                payment.mark_as_successful()
                
                # Redirect to success page
                return redirect('payment_success', payment_id=payment_id)
            except Exception as e:
                # Signature verification failed
                payment = FinePayment.objects.filter(razorpay_order_id=order_id).first()
                if payment:
                    payment_id = payment.id
                    payment.mark_as_failed(f"Signature verification failed: {str(e)}")
                    return redirect('payment_failure', payment_id=payment_id)
                else:
                    return HttpResponseBadRequest("Payment verification failed and payment record not found.")
                
        except Exception as e:
            return HttpResponseBadRequest(f"Payment callback error: {str(e)}")
    
    return HttpResponseBadRequest("Invalid request method.")

def payment_success(request, payment_id):
    try:
        payment = FinePayment.objects.get(id=payment_id)
        fine = payment.fine
        
        # Check if the user owns this payment
        if payment.user != request.user:
            messages.error(request, "You do not have permission to view this payment.")
            return redirect('user_vehicle_fines')
        
        return render(request, 'payment_success.html', {
            'payment': payment,
            'fine': fine,
            'receipt_url': reverse('payment_receipt', kwargs={'receipt_number': fine.payment_receipt_number})
        })
    except FinePayment.DoesNotExist:
        messages.error(request, "Payment not found.")
        return redirect('user_vehicle_fines')

def payment_failure(request, payment_id):
    try:
        payment = FinePayment.objects.get(id=payment_id)
        fine = payment.fine
        
        # Check if the user owns this payment
        if payment.user != request.user:
            messages.error(request, "You do not have permission to view this payment.")
            return redirect('user_vehicle_fines')
        
        return render(request, 'payment_failure.html', {
            'payment': payment,
            'fine': fine,
            'retry_url': reverse('pay_fine', kwargs={'fine_id': fine.id})
        })
    except FinePayment.DoesNotExist:
        messages.error(request, "Payment not found.")
        return redirect('user_vehicle_fines')

@login_required
def payment_receipt(request, receipt_number):
    """View for displaying payment receipt"""
    try:
        fine = VehicleFine.objects.get(payment_receipt_number=receipt_number)
        
        # Get the payment record
        payment = fine.get_latest_payment_attempt()
        
        # Check if user has permission to view this receipt
        # Allow RTO users, vehicle owners, and payment creators to view the receipt
        is_vehicle_owner = PersonalizedVehicle.objects.filter(user=request.user, vehicle=fine.vehicle).exists()
        is_payment_creator = payment and payment.user == request.user
        
        if not request.user.is_rto and not is_vehicle_owner and not is_payment_creator:
            messages.error(request, "You don't have permission to view this receipt.")
            return redirect('home')
            
        # If no payment record exists but the fine is paid, create a dummy payment record for display
        if not payment and fine.payment_status == 'Paid':
            # The FinePayment record might have been lost or not created properly
            # We'll create a temporary object just for display purposes
            from myapp.models import FinePayment
            payment = FinePayment(
                fine=fine,
                user=request.user,
                amount=fine.fine_amount,
                currency='INR',
                status='captured',
                razorpay_payment_id=fine.razorpay_payment_id or 'N/A',
                razorpay_order_id=fine.razorpay_order_id or 'N/A',
                razorpay_signature=fine.razorpay_signature or 'N/A'
            )
        
        context = {
            'fine': fine,
            'payment': payment,
            'receipt_number': receipt_number,
            'date': fine.payment_date or timezone.now(),
            'payment_date': fine.payment_date or timezone.now(),
            'vehicle': fine.vehicle,
            'amount': fine.fine_amount,
            'violation_type': fine.violation_type,
            'location': fine.location,
            'imposed_date': fine.imposed_date,
            'due_date': fine.due_date,
            'description': fine.description,
            'payment_status': fine.payment_status,
            'razorpay_order_id': fine.razorpay_order_id or 'N/A',
            'razorpay_payment_id': fine.razorpay_payment_id or 'N/A',
            'razorpay_signature': fine.razorpay_signature or 'N/A',
            'user': request.user,
        }
        
        return render(request, 'payment_receipt.html', context)
        
    except VehicleFine.DoesNotExist:
        messages.error(request, "Receipt not found.")
        return redirect('home')

def generate_receipt_pdf(fine, payment):
    """Generate a PDF receipt for the payment"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Create the content
    content = []
    
    # Add title
    content.append(Paragraph("Payment Receipt", title_style))
    
    # Add receipt details
    receipt_data = [
        ["Receipt Number:", fine.payment_receipt_number],
        ["Date:", fine.payment_date.strftime("%d/%m/%Y %H:%M")],
        ["Vehicle Number:", fine.vehicle.registration_number],
        ["Violation Type:", fine.violation_type],
        ["Location:", fine.location],
        ["Amount Paid:", f"₹{fine.fine_amount}"],
        ["Payment Status:", fine.payment_status],
        ["Payment ID:", payment.razorpay_payment_id],
        ["Order ID:", payment.razorpay_order_id],
    ]
    
    # Create table
    table = Table(receipt_data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ]))
    
    content.append(table)
    
    # Add footer
    content.append(Spacer(1, 30))
    content.append(Paragraph("This is an electronically generated receipt. No signature is required.", styles['Normal']))
    
    # Build the PDF
    doc.build(content)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    return pdf

@login_required
def download_receipt(request, receipt_number):
    """View for downloading payment receipt as PDF"""
    try:
        fine = VehicleFine.objects.get(payment_receipt_number=receipt_number)
        
        # Get the payment record
        payment = fine.get_latest_payment_attempt()
        if not payment:
            messages.error(request, "Payment record not found.")
            return redirect('home')
        
        # Check if user has permission to download this receipt
        # Allow the user who owns the vehicle OR the user who made the payment
        is_vehicle_owner = PersonalizedVehicle.objects.filter(user=request.user, vehicle=fine.vehicle).exists()
        is_payment_creator = payment.user == request.user
        
        if not request.user.is_rto and not is_vehicle_owner and not is_payment_creator:
            messages.error(request, "You don't have permission to view this receipt.")
            return redirect('home')
            
        # Generate the PDF
        pdf = generate_receipt_pdf(fine, payment)
        
        # Create the HTTP response
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{receipt_number}.pdf"'
        return response
        
    except VehicleFine.DoesNotExist:
        messages.error(request, "Receipt not found.")
        return redirect('home')

@login_required
def view_violation_document(request, fine_id):
    """View for securely serving violation documents to authorized users"""
    try:
        fine = VehicleFine.objects.get(id=fine_id)
        
        # Check if the user has permission to view this document
        user_is_authorized = False
        
        # RTO users can view all documents
        if request.user.is_rto:
            user_is_authorized = True
        
        # Vehicle owners can view their own documents
        elif PersonalizedVehicle.objects.filter(user=request.user, vehicle=fine.vehicle).exists():
            user_is_authorized = True
            
        if not user_is_authorized:
            messages.error(request, "You don't have permission to view this document.")
            return redirect('home')
            
        # Check if the fine has a document
        if not fine.violation_document:
            messages.error(request, "No document available for this fine.")
            return redirect('fine_details', fine_id=fine_id)
            
        # Get the document type
        doc_type = fine.get_document_type()
        
        # Get the file path
        file_path = fine.violation_document.path
        
        # Determine content type based on file extension
        content_type = 'application/pdf'  # Default
        if file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif file_path.lower().endswith('.png'):
            content_type = 'image/png'
                
        # Determine if this is a download request
        is_download = request.GET.get('download', '0') == '1'
        
        # Get the filename
        filename = os.path.basename(file_path)
        
        # Open the file
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type=content_type)
            
            # Set the Content-Disposition header
            if is_download:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                
            return response
            
    except VehicleFine.DoesNotExist:
        messages.error(request, "Fine not found.")
        return redirect('home')
    except FileNotFoundError:
        messages.error(request, "The document file cannot be found on the server.")
        return redirect('fine_details', fine_id=fine_id)
    except Exception as e:
        messages.error(request, f"Error accessing document: {str(e)}")
        return redirect('fine_details', fine_id=fine_id)

@login_required
def view_document(request, document_id):
    """View for securely serving document from the ViolationDocument model"""
    try:
        document = ViolationDocument.objects.get(id=document_id)
        fine = document.fine
        
        # Check if the user has permission to view this document
        user_is_authorized = False
        
        # RTO users can view all documents
        if request.user.is_rto:
            user_is_authorized = True
        
        # Vehicle owners can view their own documents
        elif PersonalizedVehicle.objects.filter(user=request.user, vehicle=fine.vehicle).exists():
            user_is_authorized = True
            
        if not user_is_authorized:
            messages.error(request, "You don't have permission to view this document.")
            return redirect('home')
            
        # Check if the document has a file
        if not document.file:
            messages.error(request, "Document file is missing.")
            return redirect('fine_details', fine_id=fine.id)
            
        # Get the document type
        doc_type = document.get_document_type()
        
        # Get the file path
        file_path = document.file.path
        
        # Determine content type based on file extension
        content_type = 'application/pdf'  # Default
        if file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif file_path.lower().endswith('.png'):
            content_type = 'image/png'
                
        # Determine if this is a download request
        is_download = request.GET.get('download', '0') == '1'
        
        # Get the filename - use original filename if available
        filename = document.original_filename or os.path.basename(file_path)
        
        # Open the file
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type=content_type)
            
            # Set the Content-Disposition header
            if is_download:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                
            return response
            
    except ViolationDocument.DoesNotExist:
        messages.error(request, "Document not found.")
        return redirect('home')
    except FileNotFoundError:
        messages.error(request, "The document file cannot be found on the server.")
        return redirect('fine_details', fine_id=fine.id if fine else 0)
    except Exception as e:
        messages.error(request, f"Error accessing document: {str(e)}")
        return redirect('fine_details', fine_id=fine.id if fine else 0)
