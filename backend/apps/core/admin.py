from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import SystemSetting, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'is_admin', 'gmail_connected', 'created_at')
    list_filter = ('is_admin', 'is_staff', 'is_active', 'gmail_connected')
    search_fields = ('email', 'name')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name', 'avatar_url', 'google_id')}),
        ('Gmail', {'fields': ('gmail_connected',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_admin', 'is_superuser', 'groups', 'user_permissions')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'google_id')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2'),
        }),
    )


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'updated_at')
    search_fields = ('key', 'value', 'description')
