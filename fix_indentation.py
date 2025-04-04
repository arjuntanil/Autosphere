#!/usr/bin/env python
# Script to fix indentation issues in views.py

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