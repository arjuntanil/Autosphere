from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
import uuid
import os

# Create your models here.

from django.contrib.auth.models import AbstractUser
from django.db import models

# class CustomUser(AbstractUser):
#     USER_TYPES = (
#         ('User', 'User'),
#         ('RTO', 'RTO'),
#     )
    
#     user_type = models.CharField(max_length=10, choices=USER_TYPES, default='User')
#     phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
#     location = models.CharField(max_length=255, null=True, blank=True)  # RTO location
#     reg_number = models.CharField(max_length=20, unique=True, null=True, blank=True)  # Unique Registration Number for RTO

#     def __str__(self):
#         return self.username


from django.db import models
from django.contrib.auth.models import AbstractUser

def user_profile_picture_path(instance, filename):
    """Generate a custom path for uploaded profile pictures"""
    # Get file extension
    ext = filename.split('.')[-1]
    # Create directory based on user ID, create unique filename
    return f'profile_pictures/{instance.id}/{uuid.uuid4().hex}.{ext}'

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('User', 'User'),
        ('RTO', 'RTO'),
    )
    
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='User')
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)  # RTO location
    reg_number = models.CharField(max_length=20, unique=True, null=True, blank=True)  # Unique Registration Number for RTO
    date_joined = models.DateTimeField(auto_now_add=True)  # This will be automatically set
    profile_picture = models.ImageField(upload_to=user_profile_picture_path, null=True, blank=True)

    def __str__(self):
        return self.username
        
    @property
    def is_rto(self):
        """Check if the user is an RTO officer"""
        return self.user_type == 'RTO'

    def clean(self):
        """Validate that phone number is provided for normal users"""
        # Only validate if this is a new user or phone number is being updated
        if self.user_type == 'User' and not self.phone_number and self._state.adding:
            raise ValidationError({'phone_number': 'Phone number is required for normal users.'})
        super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('2-wheeler', '2-wheeler'),
        ('3-wheeler', '3-wheeler'),
        ('4-wheeler', '4-wheeler'),
        ('public-transport', 'Public Transport'),
        ('heavy-vehicle', 'Heavy Vehicle (Truck etc)'),
    ]
    
    owner_name = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    color = models.CharField(max_length=50)
    chassis_number = models.CharField(max_length=50, unique=True)
    blacklist_status = models.BooleanField(default=False)
    registration_validity_date = models.DateField()
    puc_validity_date = models.DateField()
    fuel_type = models.CharField(max_length=50)
    registered_at = models.DateTimeField(auto_now_add=True)
    registration_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='4-wheeler')
    location = models.CharField(max_length=255, null=True, blank=True, help_text="Location of the RTO office where the vehicle was registered")
    registered_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_vehicles')

    def __str__(self):
        return self.registration_number
        
    def get_vehicle_type_display(self):
        """Return the display value for the vehicle type"""
        return dict(self.VEHICLE_TYPES).get(self.vehicle_type, self.vehicle_type)

class Notice(models.Model):
    """Model for notices/announcements created by RTO users"""
    
    NOTICE_TYPES = [
        ('General', 'General'),
        ('Important', 'Important'),
        ('Alert', 'Alert'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    notice_type = models.CharField(max_length=20, choices=NOTICE_TYPES, default='General')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notice'
        verbose_name_plural = 'Notices'
    
    def __str__(self):
        return self.title
    
    @property
    def is_expired(self):
        """Check if the notice has expired"""
        from django.utils import timezone  # Import inside the method to ensure availability
        if self.expires_at and self.expires_at < timezone.now():
            return True
        return False
    
    def save(self, *args, **kwargs):
        """Override save method to automatically set is_active to False if expired"""
        if self.is_expired:
            self.is_active = False
        super().save(*args, **kwargs)

class PersonalizedVehicle(models.Model):
    """Model for vehicles personalized by users"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='personalized_vehicles')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='personalized_by')
    personalized_at = models.DateTimeField(auto_now_add=True)
    nickname = models.CharField(max_length=100, null=True, blank=True)  # Optional nickname for the vehicle
    is_primary = models.BooleanField(default=False)  # Flag for primary vehicle
    registration_expiry_notified = models.BooleanField(default=False, 
        help_text="Indicates if notification has been sent for registration expiry", 
        db_index=True)
    puc_expiry_notified = models.BooleanField(default=False, 
        help_text="Indicates if notification has been sent for PUC expiry",
        db_index=True)
    
    class Meta:
        unique_together = ('user', 'vehicle')  # Each user can personalize a vehicle only once
        verbose_name = 'Personalized Vehicle'
        verbose_name_plural = 'Personalized Vehicles'
        indexes = [
            models.Index(fields=['user', 'vehicle']),
            models.Index(fields=['registration_expiry_notified']),
            models.Index(fields=['puc_expiry_notified']),
        ]
    
    def __str__(self):
        if self.nickname:
            return f"{self.nickname} ({self.vehicle.registration_number})"
        return self.vehicle.registration_number
        
    def save(self, *args, **kwargs):
        """Override save method to ensure only one primary vehicle per user"""
        if self.is_primary:
            # Set all other vehicles of this user to not primary
            PersonalizedVehicle.objects.filter(user=self.user, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

class VehicleFine(models.Model):
    """Model for fines imposed on vehicles by RTO officers"""
    VIOLATION_TYPES = [
        ('Speeding', 'Speeding'),
        ('No Parking', 'No Parking'),
        ('Wrong Side Driving', 'Wrong Side Driving'),
        ('No Helmet', 'No Helmet'),
        ('No Seatbelt', 'No Seatbelt'),
        ('Invalid Documents', 'Invalid Documents'),
        ('Signal Jumping', 'Signal Jumping'),
        ('Overloading', 'Overloading'),
        ('Invalid Number Plate', 'Invalid Number Plate'),
        ('Others', 'Others')
    ]
    
    PAYMENT_STATUS = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
        ('Contested', 'Contested'),
        ('Waived', 'Waived'),
        ('Processing', 'Processing')  # Added for payment in progress
    ]
    
    def get_violation_document_path(instance, filename):
        """Generate a custom path for uploaded violation documents"""
        # Get file extension
        ext = filename.split('.')[-1]
        # Create directory based on fine ID, create unique filename
        return f'violation_documents/{instance.id}/{uuid.uuid4().hex}.{ext}'
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='fines')
    violation_type = models.CharField(max_length=50, choices=VIOLATION_TYPES)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2)
    imposed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='imposed_fines')
    imposed_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Unpaid')
    payment_date = models.DateTimeField(null=True, blank=True)
    violation_document = models.FileField(
        upload_to=get_violation_document_path,
        null=True,
        blank=True,
        help_text="Upload a PDF document or image (JPG, JPEG, PNG) related to the violation (optional)"
    )
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=200, null=True, blank=True)
    payment_receipt_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-imposed_date']
        verbose_name = 'Vehicle Fine'
        verbose_name_plural = 'Vehicle Fines'
    
    def __str__(self):
        return f"{self.vehicle.registration_number} - {self.violation_type} - ₹{self.fine_amount}"
    
    @property
    def is_overdue(self):
        """Check if the fine is overdue for payment"""
        if self.payment_status == 'Unpaid' and self.due_date < timezone.now():
            return True
        return False
        
    @property
    def all_documents(self):
        """Get all documents related to this fine"""
        return self.documents.all()
        
    @property
    def has_documents(self):
        """Check if this fine has any documents attached"""
        return self.documents.exists()
    
    def get_document_type(self):
        """Get the type of violation document (PDF, Image, or None)"""
        if not self.violation_document:
            return None
            
        filename = self.violation_document.name.lower()
        if filename.endswith('.pdf'):
            return 'pdf'
        elif any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
            return 'image'
        else:
            return 'other'
    
    def save(self, *args, **kwargs):
        """Set due date 30 days from imposed date if not specified"""
        # Store old violation_document path before saving (for custom upload path handling)
        old_document = None
        if self.pk:
            try:
                old_fine = VehicleFine.objects.get(pk=self.pk)
                old_document = old_fine.violation_document if old_fine.violation_document else None
            except VehicleFine.DoesNotExist:
                pass
                
        if not self.due_date:
            self.due_date = timezone.now() + timezone.timedelta(days=30)
        
        # Generate receipt number if payment status is paid and no receipt number exists
        if self.payment_status == 'Paid' and not self.payment_receipt_number and self.razorpay_payment_id:
            current_time = timezone.now()
            prefix = f"FP-{current_time.strftime('%Y%m%d')}"
            random_suffix = get_random_string(length=6, allowed_chars='0123456789')
            self.payment_receipt_number = f"{prefix}-{random_suffix}"
            
            if not self.payment_date:
                self.payment_date = timezone.now()
        
        # Call the standard save method
        super().save(*args, **kwargs)
        
        # Handle the case where we're using the get_violation_document_path for file upload
        # If we create a fine without ID, we need to rename the file after we have an ID
        if old_document != self.violation_document and self.violation_document and 'violation_documents/None/' in self.violation_document.name:
            # Update the path to include the fine ID
            new_path = self.violation_document.name.replace('violation_documents/None/', f'violation_documents/{self.id}/')
            
            # Move the file to the new location
            from django.conf import settings
            old_path = os.path.join(settings.MEDIA_ROOT, self.violation_document.name)
            new_dir = os.path.join(settings.MEDIA_ROOT, f'violation_documents/{self.id}/')
            os.makedirs(new_dir, exist_ok=True)
            
            new_full_path = os.path.join(settings.MEDIA_ROOT, new_path)
            if os.path.exists(old_path):
                # Ensure the directory exists
                os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
                # Move the file
                import shutil
                shutil.move(old_path, new_full_path)
                
                # Update the model with the new path
                self.violation_document.name = new_path
                # Save again but without triggering the full save logic
                VehicleFine.objects.filter(pk=self.pk).update(violation_document=new_path)
        
    def get_payment_history(self):
        """Get the payment history for this fine"""
        return self.payments.all().order_by('-created_at')
    
    def get_latest_payment_attempt(self):
        """Get the latest payment attempt for this fine"""
        return self.payments.order_by('-created_at').first()

class FinePayment(models.Model):
    """Model for payment records related to vehicle fines"""
    fine = models.ForeignKey(VehicleFine, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='fine_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=(
        ('created', 'Created'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ), default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    receipt = models.CharField(max_length=100, blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Fine Payment'
        verbose_name_plural = 'Fine Payments'
    
    def __str__(self):
        return f"Payment {self.id} for Fine {self.fine.id}"
    
    def mark_as_successful(self):
        """Mark the payment as successful and update the fine's payment status"""
        import time
        
        self.status = 'captured'
        self.save()
        
        # Update the fine's payment status
        fine = self.fine
        fine.payment_status = 'Paid'
        fine.payment_date = timezone.now()
        # Generate a receipt number if it doesn't exist
        if not fine.payment_receipt_number:
            fine.payment_receipt_number = f"REC-{int(time.time())}-{fine.id}"
        fine.save()
        
        # Create a notification for the user
        UserNotification.objects.create(
            user=self.user,
            notification_type='payment_reminder',
            title='Fine Payment Successful',
            message=f'Your payment of ₹{self.amount} for fine ID {fine.id} was successful. Receipt Number: {fine.payment_receipt_number}',
            related_fine=fine
        )
        
        return True
    
    def mark_as_failed(self, reason=None):
        """Mark the payment as failed and update the fine's payment status"""
        self.status = 'failed'
        if reason:
            self.failure_reason = reason
        self.save()
        
        # Update the fine's payment status back to unpaid
        fine = self.fine
        fine.payment_status = 'Unpaid'
        fine.save()
        
        # Create a notification for the user
        UserNotification.objects.create(
            user=self.user,
            notification_type='payment_reminder',
            title='Fine Payment Failed',
            message=f'Your payment of ₹{self.amount} for fine ID {fine.id} failed. Reason: {reason or "Unknown error"}',
            related_fine=fine
        )
        
        return True

class UserNotification(models.Model):
    """Model for user notifications"""
    NOTIFICATION_TYPES = [
        ('fine', 'Fine Imposed'),
        ('blacklist', 'Vehicle Blacklisted'),
        ('notice', 'New Notice'),
        ('payment_reminder', 'Payment Reminder'),
        ('puc_expiry', 'PUC Expiry'),
        ('reg_expiry', 'Registration Expiry'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    related_fine = models.ForeignKey(VehicleFine, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    related_notice = models.ForeignKey(Notice, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Notification'
        verbose_name_plural = 'User Notifications'
    
    def __str__(self):
        return f"{self.notification_type} - {self.title}"
    
    @classmethod
    def create_fine_notification(cls, fine):
        """Create notifications for users who have personalized the fined vehicle"""
        # Get all users who have personalized this vehicle
        personalized_vehicles = PersonalizedVehicle.objects.filter(vehicle=fine.vehicle)
        
        for pv in personalized_vehicles:
            cls.objects.create(
                user=pv.user,
                notification_type='fine',
                title=f'New Fine Issued',
                message=f'A fine of ₹{fine.fine_amount} has been issued for your vehicle {fine.vehicle.registration_number} for {fine.violation_type}.',
                related_fine=fine
            )
    
    @classmethod
    def create_blacklist_notification(cls, vehicle):
        """Create notifications for all users who have personalized the blacklisted vehicle"""
        if vehicle.blacklist_status:
            personalized_by = PersonalizedVehicle.objects.filter(vehicle=vehicle)
            
            for personalized in personalized_by:
                notification = cls(
                    user=personalized.user,
                    notification_type='blacklist',
                    title=f"Vehicle {vehicle.registration_number} Blacklisted",
                    message=f"Your vehicle {vehicle.registration_number} has been blacklisted. Please contact your local RTO office for more information.",
                    related_vehicle=vehicle
                )
                notification.save()
    
    @classmethod
    def create_notice_notification(cls, notice):
        """Create notifications for all users about a new notice"""
        users = CustomUser.objects.filter(user_type='User')
        
        for user in users:
            notification = cls(
                user=user,
                notification_type='notice',
                title=f"New Notice: {notice.title}",
                message=f"A new notice has been published: {notice.title}",
                related_notice=notice
            )
            notification.save()

def violation_document_upload_path(instance, filename):
    """Generate a custom path for uploaded violation documents"""
    # Get file extension
    ext = filename.split('.')[-1]
    # Create a directory based on fine ID and create a unique filename
    return f'violation_documents/{instance.fine.id}/{uuid.uuid4().hex}.{ext}'


class ViolationDocument(models.Model):
    """Model for storing documents related to vehicle violations"""
    
    fine = models.ForeignKey(VehicleFine, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to=violation_document_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"Document for Fine #{self.fine.id}"
        
    def get_document_type(self):
        """Get the type of document (PDF, Image, or Other)"""
        if not self.file:
            return None
            
        filename = self.file.name.lower()
        if filename.endswith('.pdf'):
            return 'pdf'
        elif any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
            return 'image'
        else:
            return 'other'

class VehicleModificationRequest(models.Model):
    REQUEST_TYPES = [
        ('ownership', 'Ownership Transfer'),
        ('color', 'Color Change'),
        ('fuel', 'Fuel Type Change'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='modification_requests')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='modification_requests')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    current_value = models.CharField(max_length=100)
    requested_value = models.CharField(max_length=100)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rto_comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_request_type_display()} request for {self.vehicle.registration_number}"
    
    def save(self, *args, **kwargs):
        # Store current value if it's a new request
        is_new = self.pk is None
        if is_new:
            if self.request_type == 'ownership':
                self.current_value = self.vehicle.owner_name
            elif self.request_type == 'color':
                self.current_value = self.vehicle.color
            elif self.request_type == 'fuel':
                self.current_value = self.vehicle.fuel_type
        
        # Call the original save method
        super().save(*args, **kwargs)
        
        # Create notification for status changes
        if not is_new:
            # If status changed, create notification
            if self.status in ['approved', 'rejected']:
                if self.status == 'approved':
                    title = f"{self.get_request_type_display()} Request Approved"
                    message = f"Your request to change {self.vehicle.registration_number}'s {self.get_request_type_display().lower()} from '{self.current_value}' to '{self.requested_value}' has been approved."
                else:
                    title = f"{self.get_request_type_display()} Request Rejected"
                    message = f"Your request to change {self.vehicle.registration_number}'s {self.get_request_type_display().lower()} from '{self.current_value}' to '{self.requested_value}' has been rejected."
                
                if self.rto_comments:
                    message += f" Comments: {self.rto_comments}"
                
                # Create notification
                UserNotification.objects.create(
                    user=self.user,
                    notification_type='notice',
                    title=title,
                    message=message,
                    related_vehicle=self.vehicle
                )
                
                # Apply changes if approved
                if self.status == 'approved':
                    if self.request_type == 'ownership':
                        self.vehicle.owner_name = self.requested_value
                    elif self.request_type == 'color':
                        self.vehicle.color = self.requested_value
                    elif self.request_type == 'fuel':
                        self.vehicle.fuel_type = self.requested_value
                    self.vehicle.save()

class PasswordResetVerification(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    verification_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Verification for {self.user.username}"

    @classmethod
    def generate_code(cls, user, expiry_minutes=15):
        """Generate a new verification code for a user"""
        # Delete any existing unused codes for this user
        cls.objects.filter(user=user, is_used=False).delete()
        
        # Generate a 6-digit code
        code = get_random_string(length=6, allowed_chars='0123456789')
        
        # Create new verification record
        verification = cls.objects.create(
            user=user,
            verification_code=code,
            expires_at=timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        )
        return verification

    def is_valid(self):
        """Check if the verification code is still valid"""
        return not self.is_used and self.expires_at > timezone.now()
