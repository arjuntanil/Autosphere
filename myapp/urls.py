from django.urls import path
from . import views
from django.shortcuts import redirect

urlpatterns = [
    # Root path is handled by the project's urls.py
    path('home/', views.home, name='home'),
    path('rto_home/', views.rto_home, name='rto_home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register_vehicle/', views.register_vehicle, name='register_vehicle'),
    path('search_vehicle/', views.search_vehicle, name='search_vehicle'),
    path('edit_vehicle/<int:vehicle_id>/', views.edit_vehicle, name='edit_vehicle'),
    
    # Notice-related URLs
    path('notices/', views.notice_list, name='notice_list'),
    path('notices/<int:notice_id>/', views.notice_detail, name='notice_detail'),
    path('rto/notices/', views.rto_notice_list, name='rto_notice_list'),
    path('rto/notices/create/', views.create_notice, name='create_notice'),
    path('rto/notices/<int:notice_id>/edit/', views.edit_notice, name='edit_notice'),
    path('rto/notices/<int:notice_id>/delete/', views.delete_notice, name='delete_notice'),
    
    # Vehicle personalization URLs
    path('my-vehicles/', views.personalized_vehicles, name='personalized_vehicles'),
    path('personalize-vehicle/<str:registration_number>/', views.personalize_vehicle, name='personalize_vehicle'),
    path('my-vehicles/set-primary/<int:id>/', views.set_primary_vehicle, name='set_primary_vehicle'),
    path('my-vehicles/remove/<int:id>/', views.remove_personalized_vehicle, name='remove_personalized_vehicle'),

    # Fine-related URLs
    path('rto/fines/', views.rto_fine_list, name='rto_fine_list'),
    path('rto/fines/impose/', views.impose_fine, name='impose_fine'),
    path('rto/fines/<int:fine_id>/update-status/', views.update_fine_status, name='update_fine_status'),
    path('rto/fines/<int:fine_id>/delete/', views.delete_fine, name='delete_fine'),
    path('my-vehicles/fines/', views.user_vehicle_fines, name='user_vehicle_fines'),
    path('fines/<int:fine_id>/', views.fine_details, name='fine_details'),
    
    # Payment URLs
    path('fines/<int:fine_id>/pay/', views.pay_fine, name='pay_fine'),
    path('fines/payment/callback/', views.payment_callback, name='payment_callback'),
    path('fines/payment/<int:payment_id>/success/', views.payment_success, name='payment_success'),
    path('fines/payment/<int:payment_id>/failure/', views.payment_failure, name='payment_failure'),
    path('fines/payment/receipt/<str:receipt_number>/', views.payment_receipt, name='payment_receipt'),
    path('fines/payment/receipt/<str:receipt_number>/download/', views.download_receipt, name='download_receipt'),
    
    # Notification URLs - Updated to match template references
    path('notifications/', views.user_notifications, name='notifications'),  # Changed from 'user_notifications'
    path('notifications/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('get-notification-count/', views.get_notification_count, name='get_notification_count'),  # Changed from 'api/notifications/count/'
    
    # Vehicle Modification Request URLs
    path('my-vehicles/modification-requests/', views.user_modification_requests, name='user_modification_requests'),
    path('my-vehicles/<int:vehicle_id>/request-modification/', views.create_modification_request, name='create_modification_request'),
    path('my-vehicles/modification-requests/<int:request_id>/', views.modification_request_detail, name='modification_request_detail'),
    path('my-vehicles/modification-requests/<int:request_id>/delete/', views.delete_modification_request, name='delete_modification_request'),
    
    # RTO Modification Request URLs
    path('rto/modification-requests/', views.rto_modification_requests, name='rto_modification_requests'),
    path('rto/modification-requests/<int:request_id>/', views.rto_modification_request_detail, name='rto_modification_request_detail'),
    
    # Media serving URL
    path('media/<path:path>/', views.serve_media_file, name='serve_media_file'),
    
    # Debug view for PDF files 
    path('debug/pdf-files/', views.debug_pdf_files, name='debug_pdf_files'),
    
    # Redirect the root URL to 'home'
    path('', lambda request: redirect('home'), name='index'),

    # Profile URLs
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),

    # Password Reset URLs
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('verify-code/', views.verify_code, name='verify_code'),
    path('reset-password/', views.reset_password, name='reset_password'),
]


# from django.urls import path
# from myapp import views

# urlpatterns = [
#     path('home/', views.home, name='home'),
#     path('rto_home/', views.rto_home, name='rto_home'),
#     path('register/', views.register, name='register'),
#     path('login/', views.login_view, name='login'),  # Ensure login route exists
#     path('logout/', views.logout_view, name='logout'),
#     path('register_vehicle/', views.register_vehicle, name='register_vehicle'),
#     path('search_vehicle/', views.search_vehicle, name='search_vehicle'),
# ]
