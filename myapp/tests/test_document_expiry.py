from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.core.management import call_command
from io import StringIO

from myapp.models import CustomUser, Vehicle, PersonalizedVehicle, UserNotification

class DocumentExpiryTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123',
            user_type='User',
            phone_number='1234567890'
        )
        
        # Create vehicles with different expiry dates
        # Vehicle with registration expiring in 2 days
        self.reg_expiring_vehicle = Vehicle.objects.create(
            owner_name='Test Owner',
            manufacturer='Toyota',
            model='Corolla',
            color='Blue',
            chassis_number='CHASSIS001',
            blacklist_status=False,
            registration_validity_date=timezone.now().date() + timedelta(days=2),
            puc_validity_date=timezone.now().date() + timedelta(days=60),
            fuel_type='Petrol',
            registration_number='RJ01AB1001'
        )
        
        # Vehicle with PUC expiring in 2 days
        self.puc_expiring_vehicle = Vehicle.objects.create(
            owner_name='Test Owner',
            manufacturer='Honda',
            model='City',
            color='Red',
            chassis_number='CHASSIS002',
            blacklist_status=False,
            registration_validity_date=timezone.now().date() + timedelta(days=60),
            puc_validity_date=timezone.now().date() + timedelta(days=2),
            fuel_type='Petrol',
            registration_number='RJ01AB1002'
        )
        
        # Vehicle with both documents valid
        self.valid_vehicle = Vehicle.objects.create(
            owner_name='Test Owner',
            manufacturer='Hyundai',
            model='i20',
            color='Silver',
            chassis_number='CHASSIS003',
            blacklist_status=False,
            registration_validity_date=timezone.now().date() + timedelta(days=60),
            puc_validity_date=timezone.now().date() + timedelta(days=60),
            fuel_type='Petrol',
            registration_number='RJ01AB1003'
        )
        
        # Personalize the vehicles
        PersonalizedVehicle.objects.create(
            user=self.user,
            vehicle=self.reg_expiring_vehicle,
            nickname='My Toyota',
            is_primary=True
        )
        
        PersonalizedVehicle.objects.create(
            user=self.user,
            vehicle=self.puc_expiring_vehicle,
            nickname='My Honda'
        )
        
        PersonalizedVehicle.objects.create(
            user=self.user,
            vehicle=self.valid_vehicle,
            nickname='My Hyundai'
        )
    
    def test_document_expiry_check(self):
        """Test that the command sends notifications for expiring documents"""
        # Initial counts
        initial_notifications = UserNotification.objects.count()
        
        # Call the command
        out = StringIO()
        call_command('check_document_expiry', stdout=out)
        
        # Check that notifications were created
        new_notification_count = UserNotification.objects.count() - initial_notifications
        self.assertEqual(new_notification_count, 2)  # One for registration, one for PUC
        
        # Check the specific notifications
        reg_notification = UserNotification.objects.filter(
            notification_type='reg_expiry',
            related_vehicle=self.reg_expiring_vehicle
        ).first()
        self.assertIsNotNone(reg_notification)
        self.assertEqual(reg_notification.user, self.user)
        self.assertFalse(reg_notification.is_read)
        
        puc_notification = UserNotification.objects.filter(
            notification_type='puc_expiry',
            related_vehicle=self.puc_expiring_vehicle
        ).first()
        self.assertIsNotNone(puc_notification)
        self.assertEqual(puc_notification.user, self.user)
        self.assertFalse(puc_notification.is_read)
        
        # Check the notification flags were set
        reg_personalized = PersonalizedVehicle.objects.get(vehicle=self.reg_expiring_vehicle)
        self.assertTrue(reg_personalized.registration_expiry_notified)
        
        puc_personalized = PersonalizedVehicle.objects.get(vehicle=self.puc_expiring_vehicle)
        self.assertTrue(puc_personalized.puc_expiry_notified)
        
        # Run the command again
        call_command('check_document_expiry', stdout=StringIO())
        
        # No new notifications should be created
        after_second_run = UserNotification.objects.count()
        self.assertEqual(after_second_run, initial_notifications + 2)
    
    def test_reset_notification_flags(self):
        """Test that notification flags are reset when documents are renewed"""
        # First, mark a vehicle as notified
        pv = PersonalizedVehicle.objects.get(vehicle=self.reg_expiring_vehicle)
        pv.registration_expiry_notified = True
        pv.save()
        
        # Now renew the registration
        self.reg_expiring_vehicle.registration_validity_date = timezone.now().date() + timedelta(days=365)
        self.reg_expiring_vehicle.save()
        
        # Run the command
        call_command('check_document_expiry', stdout=StringIO())
        
        # Check that the flag was reset
        pv.refresh_from_db()
        self.assertFalse(pv.registration_expiry_notified) 