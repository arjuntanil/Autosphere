from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Vehicle, Notice, PersonalizedVehicle, VehicleFine, UserNotification, VehicleModificationRequest

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'phone_number', 'date_of_birth')
    list_filter = ('user_type', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth')}),
        ('Additional Info', {'fields': ('user_type', 'location', 'reg_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type', 'phone_number', 'date_of_birth'),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('username',)

class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'owner_name', 'manufacturer', 'model', 'registration_validity_date')
    list_filter = ('fuel_type', 'blacklist_status')
    search_fields = ('registration_number', 'owner_name', 'chassis_number')

class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'notice_type', 'created_by', 'created_at', 'is_active', 'expires_at', 'is_expired')
    list_filter = ('notice_type', 'is_active', 'created_at')
    search_fields = ('title', 'content', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = "Expired"

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Vehicle, VehicleAdmin)
admin.site.register(Notice, NoticeAdmin)
