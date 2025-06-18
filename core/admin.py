# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, School, Subject, Class, TeacherProfile, StudentProfile,
    Project, ProjectParticipation, EnvironmentalImpact, Donation,
    Certificate, SchoolMembership
)

# Custom User Admin
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'city', 'country', 'is_staff')
    list_filter = ('role', 'gender', 'country', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'mobile_number', 'gender', 'date_of_birth', 'city', 'country', 'profile_picture')
        }),
    )

# School Admin
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'institution_type', 'affiliation', 'number_of_students', 'admin')
    list_filter = ('institution_type', 'affiliation', 'country', 'city')
    search_fields = ('name', 'city', 'country', 'principal_name')
    readonly_fields = ('id', 'created_at', 'updated_at')

# Subject Admin
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    search_fields = ('name',)

# Class Admin
@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'description')
    list_filter = ('school',)
    search_fields = ('name', 'school__name')

# Teacher Profile Admin
@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'teacher_role', 'status')
    list_filter = ('teacher_role', 'status', 'school')
    search_fields = ('user__first_name', 'user__last_name', 'school__name')
    filter_horizontal = ('assigned_subjects', 'assigned_classes')

# Student Profile Admin
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'current_class', 'student_id', 'enrollment_date')
    list_filter = ('school', 'current_class', 'enrollment_date')
    search_fields = ('user__first_name', 'user__last_name', 'school__name', 'student_id')

# Project Admin
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'lead_school', 'status', 'start_date', 'end_date', 'created_by')
    list_filter = ('status', 'start_date', 'is_open_for_collaboration')
    search_fields = ('title', 'short_description', 'lead_school__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    # Remove filter_horizontal for participating_schools since it uses through model

# Project Participation Admin
@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(admin.ModelAdmin):
    list_display = ('project', 'school', 'is_active', 'joined_at')
    list_filter = ('is_active', 'joined_at')
    search_fields = ('project__title', 'school__name')

# Environmental Impact Admin
@admin.register(EnvironmentalImpact)
class EnvironmentalImpactAdmin(admin.ModelAdmin):
    list_display = ('project', 'school', 'impact_type', 'value', 'unit', 'verified', 'measurement_date')
    list_filter = ('impact_type', 'verified', 'measurement_date', 'project')
    search_fields = ('project__title', 'school__name')

# Donation Admin
@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('donor_name', 'amount', 'purpose', 'payment_status', 'created_at')
    list_filter = ('purpose', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('donor_name', 'donor_email', 'recipient_name')
    readonly_fields = ('id', 'created_at')  # Removed updated_at since it doesn't exist

# Certificate Admin
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'certificate_type', 'title', 'project', 'issued_by', 'issued_at')
    list_filter = ('certificate_type', 'issued_at', 'project')
    search_fields = ('recipient__first_name', 'recipient__last_name', 'title')
    readonly_fields = ('id', 'issued_at')

# School Membership Admin
@admin.register(SchoolMembership)
class SchoolMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'is_active', 'joined_at')
    list_filter = ('is_active', 'joined_at')
    search_fields = ('user__first_name', 'user__last_name', 'school__name')