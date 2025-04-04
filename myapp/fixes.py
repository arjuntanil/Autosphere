# Function 1: Fix for get_notification_count
def get_notification_count(request):
    """API endpoint to get the number of unread notifications for a user"""
    if request.user.is_authenticated:
        count = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})

# Function 2: Fix for rto_modification_requests (line 1045-1050)
@login_required
def rto_modification_requests(request):
    """View for RTO users to see all modification requests"""
    if not request.user.is_rto:
        messages.error(request, "You don't have permission to view this page")
        return redirect('home')
    
    # Get the RTO user's region code from their username (assuming format RTO-XX where XX is the region code)
    rto_reg_number = request.user.reg_number
    
    # Filter requests based on RTO jurisdiction
    # Get vehicles with registration numbers starting with the RTO's code
    requests = VehicleModificationRequest.objects.filter(
        vehicle__registration_number__startswith=f"KL {rto_reg_number}"
    ).order_by('-created_at')
    
    # Apply filters if provided
    status = request.GET.get('status', '')
    if status and status != 'All':
        requests = requests.filter(status=status)
        
    return render(request, 'rto_modification_requests.html', {
        'requests': requests,
        'status_filter': status,
        'status_choices': VehicleModificationRequest.STATUS_CHOICES
    }) 