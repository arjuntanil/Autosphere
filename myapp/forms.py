from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, Vehicle, Notice, PersonalizedVehicle, VehicleFine, VehicleModificationRequest
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
import re
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone_number', 'date_of_birth', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set user_type to 'User' by default
        self.instance.user_type = 'User'
        
        # Update field labels and help text
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['password1'].help_text = 'Your password must contain at least 8 characters.'
        self.fields['phone_number'].help_text = 'Enter your 10-digit phone number.'
        self.fields['date_of_birth'].help_text = 'Enter your date of birth.'
        
        # Make fields required
        self.fields['phone_number'].required = True
        self.fields['date_of_birth'].required = True
        
        # Add widgets for better input
        self.fields['date_of_birth'].widget = forms.DateInput(attrs={'type': 'date'})
        self.fields['phone_number'].widget = forms.TextInput(attrs={'pattern': '[0-9]{10}'})

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        if phone_number and len(phone_number) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone_number

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if date_of_birth:
            today = timezone.now().date()
            if date_of_birth >= today:
                raise forms.ValidationError("Date of birth cannot be in the future.")
            if (today.year - date_of_birth.year) < 18:
                raise forms.ValidationError("You must be at least 18 years old to register.")
        return date_of_birth

class VehicleRegistrationForm(forms.ModelForm):
    registration_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter registration number (e.g., AB 5500)'
        })
    )
    use_manual_entry = forms.BooleanField(
        required=False,
        initial=False,
        label="Manual Entry",
        help_text="Check this to manually enter the registration number"
    )

    class Meta:
        model = Vehicle
        fields = ['owner_name', 'manufacturer', 'model', 'color', 'chassis_number', 
                  'blacklist_status', 'registration_validity_date', 'puc_validity_date', 
                  'fuel_type', 'registration_number']

    def clean_registration_number(self):
        registration_number = self.cleaned_data.get('registration_number')
        use_manual_entry = self.cleaned_data.get('use_manual_entry')
        
        if not use_manual_entry:
            return registration_number
            
        if not registration_number:
            raise forms.ValidationError("Registration number is required when using manual entry.")
            
        # Clean and normalize the input
        clean_input = registration_number.upper().strip()
        
        # Validate format: 1-2 uppercase letters followed by 4 digits
        if not re.match(r'^[A-Z]{1,2}\s*\d{4}$', clean_input):
            raise forms.ValidationError("Invalid format. Use 1-2 uppercase letters followed by 4 digits (e.g., AB 5500)")
            
        # Check if the number is within valid range (0001-9999)
        number_part = int(clean_input.split()[-1])
        if number_part < 1 or number_part > 9999:
            raise forms.ValidationError("Number must be between 0001 and 9999")
            
        # Check if registration number already exists
        if Vehicle.objects.filter(registration_number__iexact=clean_input).exists():
            raise forms.ValidationError("This registration number is already in use")
            
        return clean_input

class NoticeForm(forms.ModelForm):
    """Form for creating and editing notices"""
    
    NOTICE_TYPES = [
        ('General', 'General'),
        ('Important', 'Important'),
        ('Alert', 'Alert'),
    ]
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Enter a clear and concise title for the notice."
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        help_text="Enter the full content of the notice."
    )
    notice_type = forms.ChoiceField(
        choices=NOTICE_TYPES,
        initial='General',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select the type of notice to categorize its importance."
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        help_text="If checked, the notice will be visible to users. Uncheck to hide the notice."
    )
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        help_text="Optional. If set, the notice will automatically become inactive after this date and time."
    )
    
    class Meta:
        model = Notice
        fields = ['title', 'content', 'notice_type', 'is_active', 'expires_at']

    def clean_expires_at(self):
        expires_at = self.cleaned_data.get('expires_at')
        if expires_at and expires_at <= timezone.now():
            raise forms.ValidationError("Expiration date must be in the future")
        return expires_at

class VehicleVerificationForm(forms.Form):
    """Form for verifying vehicle ownership before personalization"""
    registration_number = forms.CharField(max_length=20, disabled=True, required=False)
    chassis_number = forms.CharField(max_length=50, 
                                   widget=forms.TextInput(attrs={'placeholder': 'Enter chassis number for verification'}))
    nickname = forms.CharField(max_length=100, required=False,
                              widget=forms.TextInput(attrs={'placeholder': 'Give your vehicle a nickname (optional)'}))
    
    def __init__(self, *args, **kwargs):
        self.vehicle = kwargs.pop('vehicle', None)
        super().__init__(*args, **kwargs)
        if self.vehicle:
            self.fields['registration_number'].initial = self.vehicle.registration_number
    
    def clean_chassis_number(self):
        chassis_number = self.cleaned_data.get('chassis_number')
        if not self.vehicle:
            raise forms.ValidationError('Vehicle information is missing.')
            
        if self.vehicle.chassis_number != chassis_number:
            raise forms.ValidationError('The chassis number does not match our records. Please try again.')
            
        return chassis_number

class VehicleFineForm(forms.ModelForm):
    """Form for imposing fines on vehicles by RTO users"""
    registration_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter vehicle registration number'}),
        label="Vehicle Registration Number"
    )
    
    class Meta:
        model = VehicleFine
        fields = ['violation_type', 'description', 'location', 'fine_amount', 'due_date']
        widgets = {
            'violation_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the violation details'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter location of violation'}),
            'fine_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter fine amount in ₹'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default due date to 30 days from now
        self.fields['due_date'].initial = timezone.now() + timezone.timedelta(days=30)
        
    def clean_registration_number(self):
        registration_number = self.cleaned_data.get('registration_number')
        try:
            vehicle = Vehicle.objects.get(registration_number=registration_number)
            # Store vehicle instance to use in save method
            self.vehicle = vehicle
        except Vehicle.DoesNotExist:
            raise ValidationError("No vehicle found with this registration number")
        return registration_number
        
    def save(self, commit=True):
        fine = super().save(commit=False)
        fine.vehicle = self.vehicle
        if commit:
            fine.save()
        return fine

class FineForm(forms.ModelForm):
    """Form for RTO users to impose fines on vehicles"""
    vehicle_registration_number = forms.CharField(
        max_length=20,
        label="Vehicle Registration Number",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter vehicle registration number (e.g. KL 06 0001)'
        })
    )
    
    class Meta:
        model = VehicleFine
        fields = ['violation_type', 'description', 'location', 'fine_amount', 'due_date', 'violation_document']
        widgets = {
            'violation_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe the violation',
                'rows': 3
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Location where violation occurred'
            }),
            'fine_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Amount in ₹'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'violation_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default due date to 30 days from now
        today = timezone.now().date()
        self.fields['due_date'].initial = today + timezone.timedelta(days=30)
    
    def clean_vehicle_registration_number(self):
        """Validate that the registration number exists in the database"""
        reg_number = self.cleaned_data.get('vehicle_registration_number')
        
        # This will be handled in the view with normalize_registration_number
        # to provide better feedback to the user
        return reg_number
        
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        today = timezone.now().date()
        
        if due_date:
            # Convert datetime to date if necessary
            if hasattr(due_date, 'date'):
                due_date = due_date.date()
                
            if due_date < today:
                raise forms.ValidationError("Due date cannot be in the past")
        
        return due_date
        
    def clean_violation_document(self):
        """Validate that the uploaded file is a PDF document"""
        document = self.cleaned_data.get('violation_document')
        
        if document:
            # Check file extension
            file_ext = os.path.splitext(document.name)[1].lower()
            if file_ext != '.pdf':
                raise forms.ValidationError("Only PDF files are allowed.")
                
            # Check file size (limit to 5MB)
            if document.size > 5 * 1024 * 1024:  # 5MB in bytes
                raise forms.ValidationError("File size must be under 5MB.")
                
            # Validate MIME type (optional additional check)
            if hasattr(document, 'content_type') and document.content_type != 'application/pdf':
                raise forms.ValidationError("File type must be PDF.")
                
        return document
    
    def clean_fine_amount(self):
        amount = self.cleaned_data.get('fine_amount')
        
        if amount and amount <= 0:
            raise forms.ValidationError("Fine amount must be greater than zero")
        
        return amount

class VehicleModificationRequestForm(forms.ModelForm):
    class Meta:
        model = VehicleModificationRequest
        fields = ['request_type', 'requested_value', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'requested_value': forms.TextInput(attrs={'class': 'form-control'}),
            'request_type': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        self.vehicle = kwargs.pop('vehicle', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Update the label based on request type
        self.fields['request_type'].label = "Modification Type"
        self.fields['requested_value'].label = "New Value"
        self.fields['reason'].label = "Reason for Request"
        
        # Add descriptions
        self.fields['request_type'].help_text = "Select the type of modification you want to request"
        self.fields['requested_value'].help_text = "Enter the new value you want to change to"
        self.fields['reason'].help_text = "Provide a reason for this modification request"
    
    def clean(self):
        cleaned_data = super().clean()
        request_type = cleaned_data.get('request_type')
        requested_value = cleaned_data.get('requested_value')
        
        # Validate requested value based on request type
        if request_type == 'ownership':
            if not requested_value or len(requested_value.strip()) < 3:
                raise forms.ValidationError("Owner name must be at least 3 characters long")
        elif request_type == 'color':
            if not requested_value or len(requested_value.strip()) < 3:
                raise forms.ValidationError("Color must be at least 3 characters long")
        elif request_type == 'fuel':
            valid_fuel_types = ['Petrol', 'Diesel', 'Electric', 'CNG', 'LPG', 'Hybrid']
            if requested_value not in valid_fuel_types:
                raise forms.ValidationError(f"Fuel type must be one of: {', '.join(valid_fuel_types)}")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.user
        instance.vehicle = self.vehicle
        
        if commit:
            instance.save()
        return instance


class ModificationRequestUpdateForm(forms.ModelForm):
    class Meta:
        model = VehicleModificationRequest
        fields = ['status', 'rto_comments']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'rto_comments': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].label = "Request Status"
        self.fields['rto_comments'].label = "Comments"
        self.fields['rto_comments'].required = False
        self.fields['rto_comments'].help_text = "Provide comments/reason, especially if rejecting the request"

class PasswordResetRequestForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')

        try:
            user = User.objects.get(username=username, email=email)
        except User.DoesNotExist:
            raise ValidationError(_('No user found with this username and email combination.'))

        return cleaned_data

class VerificationCodeForm(forms.Form):
    verification_code = forms.CharField(
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit code'
        })
    )

class PasswordResetForm(forms.Form):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError(_('Passwords do not match.'))

        if len(password1) < 8:
            raise ValidationError(_('Password must be at least 8 characters long.'))

        return cleaned_data
