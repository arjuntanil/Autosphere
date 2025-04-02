# Vehicle Document Expiry Notification System

This system checks vehicle documents (Registration & PUC Certificates) for upcoming expiration and notifies users ahead of time.

## Features

1. **Proactive Notifications:**
   - Sends notifications 3 days before document expiry
   - Includes specific information about which document is expiring
   - Prevents duplicate notifications

2. **Visual Indicators:**
   - Red warnings for expired documents
   - Yellow warnings for documents expiring within 7 days
   - Shows exact days remaining or days since expiration

3. **Management Command:**
   - Runs daily via cron/scheduled task
   - Sends expiry notifications
   - Resets notification flags for renewed documents

## Setup Instructions

### 1. Database Migrations

The system requires additional fields in the `PersonalizedVehicle` model to track notification status. These have already been migrated with proper indexing for performance.

### 2. Setting Up Scheduled Task

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Click "Create Basic Task..."
3. Name: "AutoSphere Document Expiry Check"
4. Description: "Checks for vehicle documents expiring in 3 days and sends notifications"
5. Trigger: Daily at 12:00 AM
6. Action: Start a program
7. Program/script: `D:\AutoSphere\scripts\check_document_expiry.bat`
8. Start in: `D:\AutoSphere`
9. Click Finish

#### Linux (Cron)

Add the following cron job to run daily at midnight:

```bash
0 0 * * * cd /path/to/your/project && /path/to/venv/bin/python manage.py check_document_expiry >> /path/to/logs/document_expiry.log 2>&1
```

### 3. Testing

To test the system without waiting for the scheduled task:

```bash
python manage.py check_document_expiry
```

To create a test case where a document expires in 3 days (for testing notifications):

```python
# In Django shell
from django.utils import timezone
from datetime import timedelta
from myapp.models import Vehicle

# Set a vehicle's registration to expire in 3 days
vehicle = Vehicle.objects.get(registration_number='YOUR_VEHICLE_NUMBER')
vehicle.registration_validity_date = timezone.now().date() + timedelta(days=3)
vehicle.save()
```

## Implementation Details

### Models
- Added fields to `PersonalizedVehicle`:
  - `registration_expiry_notified` (boolean, indexed)
  - `puc_expiry_notified` (boolean, indexed)
- Added database indexes for improved query performance

### Management Command
- Main logic in `check_document_expiry.py`
- Uses database transactions for atomicity
- Has error handling for notification failures
- Checks exactly 3 days before expiration
- Provides detailed logging for monitoring

### Views
- `personalized_vehicles` view shows document expiry status
- Adds warning indicators with color coding

## Troubleshooting

If notifications aren't being sent:

1. Check the `logs/document_expiry.log` file for any errors
2. Verify that the Task Scheduler/cron job is running correctly
3. Check if there are any vehicles with documents expiring exactly 3 days from today
4. Ensure the notification flags haven't been set (a notification is only sent once per expiry event)

To reset notification flags for testing:

```python
# In Django shell
from myapp.models import PersonalizedVehicle
PersonalizedVehicle.objects.update(registration_expiry_notified=False, puc_expiry_notified=False)
``` 