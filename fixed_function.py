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