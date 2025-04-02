from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from datetime import timedelta
import logging

from myapp.models import PersonalizedVehicle, UserNotification

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Checks for vehicle document expiry and sends notifications'

    def handle(self, *args, **options):
        self.stdout.write('Starting document expiry check...')
        
        # Today and notification threshold (3 days from now)
        today = timezone.now().date()
        notification_threshold = today + timedelta(days=3)
        
        # Get all personalized vehicles with prefetched vehicle data
        personalized_vehicles = PersonalizedVehicle.objects.select_related(
            'user', 'vehicle'
        ).filter(
            # Either registration or PUC is not expired but close to expiry
            # and notification hasn't been sent yet
            (
                # Registration near expiry and not notified
                (
                    Q(vehicle__registration_validity_date__isnull=False) &
                    Q(vehicle__registration_validity_date=notification_threshold) &
                    Q(registration_expiry_notified=False)
                ) |
                # PUC near expiry and not notified
                (
                    Q(vehicle__puc_validity_date__isnull=False) &
                    Q(vehicle__puc_validity_date=notification_threshold) &
                    Q(puc_expiry_notified=False)
                )
            )
        )
        
        registration_notifications = 0
        puc_notifications = 0
        
        # Transaction to ensure all updates are atomic
        with transaction.atomic():
            for personalized_vehicle in personalized_vehicles:
                # Check registration expiry
                if (personalized_vehicle.vehicle.registration_validity_date == notification_threshold and
                        not personalized_vehicle.registration_expiry_notified):
                    try:
                        # Create notification
                        UserNotification.objects.create(
                            user=personalized_vehicle.user,
                            notification_type='reg_expiry',
                            title='Vehicle Registration Expiring Soon',
                            message=f'The registration for your vehicle {personalized_vehicle.vehicle.registration_number} will expire in 3 days. Please renew it as soon as possible.',
                            related_vehicle=personalized_vehicle.vehicle,
                            is_read=False
                        )
                        
                        # Mark as notified
                        personalized_vehicle.registration_expiry_notified = True
                        personalized_vehicle.save(update_fields=['registration_expiry_notified'])
                        
                        registration_notifications += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create registration expiry notification for vehicle {personalized_vehicle.vehicle.registration_number}: {str(e)}")
                
                # Check PUC expiry
                if (personalized_vehicle.vehicle.puc_validity_date == notification_threshold and
                        not personalized_vehicle.puc_expiry_notified):
                    try:
                        # Create notification
                        UserNotification.objects.create(
                            user=personalized_vehicle.user,
                            notification_type='puc_expiry',
                            title='PUC Certificate Expiring Soon',
                            message=f'The PUC certificate for your vehicle {personalized_vehicle.vehicle.registration_number} will expire in 3 days. Please renew it as soon as possible.',
                            related_vehicle=personalized_vehicle.vehicle,
                            is_read=False
                        )
                        
                        # Mark as notified
                        personalized_vehicle.puc_expiry_notified = True
                        personalized_vehicle.save(update_fields=['puc_expiry_notified'])
                        
                        puc_notifications += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create PUC expiry notification for vehicle {personalized_vehicle.vehicle.registration_number}: {str(e)}")
        
        # Reset notification flags for documents that have been renewed
        with transaction.atomic():
            # Reset registration notification flag if date has been updated
            PersonalizedVehicle.objects.filter(
                registration_expiry_notified=True,
                vehicle__registration_validity_date__gt=notification_threshold
            ).update(registration_expiry_notified=False)
            
            # Reset PUC notification flag if date has been updated
            PersonalizedVehicle.objects.filter(
                puc_expiry_notified=True,
                vehicle__puc_validity_date__gt=notification_threshold
            ).update(puc_expiry_notified=False)
        
        self.stdout.write(self.style.SUCCESS(
            f'Document expiry check completed. Sent {registration_notifications} registration and {puc_notifications} PUC notifications.'
        )) 