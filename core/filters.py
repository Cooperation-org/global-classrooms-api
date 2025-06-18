"""
Custom filters for Global Classrooms API
Provides advanced filtering and search capabilities
"""

import django_filters
from django.db import models
from django.db.models import Q
from .models import (
    User, School, Project, EnvironmentalImpact, 
    Donation, Certificate, TeacherProfile, StudentProfile
)


class UserFilter(django_filters.FilterSet):
    """Advanced filtering for users"""
    
    # Text searches
    name = django_filters.CharFilter(method='filter_by_name', label='Search by name')
    email = django_filters.CharFilter(lookup_expr='icontains', label='Email contains')
    
    # Role and status filters
    role = django_filters.ChoiceFilter(choices=User.USER_ROLES)
    is_active = django_filters.BooleanFilter()
    
    # Location filters
    country = django_filters.CharFilter(lookup_expr='iexact')
    city = django_filters.CharFilter(lookup_expr='icontains')
    
    # Date filters
    joined_after = django_filters.DateFilter(field_name='date_joined', lookup_expr='gte')
    joined_before = django_filters.DateFilter(field_name='date_joined', lookup_expr='lte')
    
    # Age filters
    min_age = django_filters.NumberFilter(method='filter_by_min_age')
    max_age = django_filters.NumberFilter(method='filter_by_max_age')
    
    class Meta:
        model = User
        fields = ['role', 'gender', 'country', 'city', 'is_active']
    
    def filter_by_name(self, queryset, name, value):
        """Filter by first name or last name"""
        return queryset.filter(
            Q(first_name__icontains=value) | Q(last_name__icontains=value)
        )
    
    def filter_by_min_age(self, queryset, name, value):
        """Filter by minimum age"""
        from django.utils import timezone
        from datetime import timedelta
        
        max_birth_date = timezone.now().date() - timedelta(days=value * 365)
        return queryset.filter(date_of_birth__lte=max_birth_date)
    
    def filter_by_max_age(self, queryset, name, value):
        """Filter by maximum age"""
        from django.utils import timezone
        from datetime import timedelta
        
        min_birth_date = timezone.now().date() - timedelta(days=value * 365)
        return queryset.filter(date_of_birth__gte=min_birth_date)


class SchoolFilter(django_filters.FilterSet):
    """Advanced filtering for schools"""
    
    # Text searches
    name = django_filters.CharFilter(lookup_expr='icontains', label='School name contains')
    principal = django_filters.CharFilter(field_name='principal_name', lookup_expr='icontains')
    
    # Location filters
    country = django_filters.CharFilter(lookup_expr='iexact')
    city = django_filters.CharFilter(lookup_expr='icontains')
    state = django_filters.CharFilter(lookup_expr='icontains')
    
    # Type and affiliation filters
    institution_type = django_filters.ChoiceFilter(choices=School.INSTITUTION_TYPES)
    affiliation = django_filters.ChoiceFilter(choices=School.AFFILIATION_TYPES)
    medium_of_instruction = django_filters.ChoiceFilter(choices=School.MEDIUM_OF_INSTRUCTION)
    
    # Size filters
    min_students = django_filters.NumberFilter(field_name='number_of_students', lookup_expr='gte')
    max_students = django_filters.NumberFilter(field_name='number_of_students', lookup_expr='lte')
    min_teachers = django_filters.NumberFilter(field_name='number_of_teachers', lookup_expr='gte')
    max_teachers = django_filters.NumberFilter(field_name='number_of_teachers', lookup_expr='lte')
    
    # Date filters
    established_after = django_filters.NumberFilter(field_name='year_of_establishment', lookup_expr='gte')
    established_before = django_filters.NumberFilter(field_name='year_of_establishment', lookup_expr='lte')
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    # Status filters
    is_verified = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = School
        fields = [
            'institution_type', 'affiliation', 'country', 'city', 
            'medium_of_instruction', 'is_verified', 'is_active'
        ]


class ProjectFilter(django_filters.FilterSet):
    """Advanced filtering for projects"""
    
    # Text searches
    title = django_filters.CharFilter(lookup_expr='icontains', label='Title contains')
    description = django_filters.CharFilter(field_name='short_description', lookup_expr='icontains')
    
    # Theme filters
    environmental_theme = django_filters.CharFilter(method='filter_by_theme')
    
    # Status and timeline filters
    status = django_filters.ChoiceFilter(choices=Project.STATUS_CHOICES)
    is_open_for_collaboration = django_filters.BooleanFilter()
    offer_rewards = django_filters.BooleanFilter()
    
    # Date filters
    start_date_after = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')
    end_date_after = django_filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date_before = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    # School filters
    lead_school = django_filters.ModelChoiceFilter(queryset=School.objects.all())
    lead_school_country = django_filters.CharFilter(field_name='lead_school__country', lookup_expr='iexact')
    lead_school_city = django_filters.CharFilter(field_name='lead_school__city', lookup_expr='icontains')
    
    # Contact filters
    contact_country = django_filters.CharFilter(lookup_expr='iexact')
    contact_city = django_filters.CharFilter(lookup_expr='icontains')
    
    # Participation filters
    has_participation = django_filters.BooleanFilter(method='filter_has_participation')
    min_participants = django_filters.NumberFilter(method='filter_min_participants')
    
    class Meta:
        model = Project
        fields = [
            'status', 'is_open_for_collaboration', 'offer_rewards',
            'lead_school', 'contact_country', 'contact_city'
        ]
    
    def filter_by_theme(self, queryset, name, value):
        """Filter by environmental theme"""
        return queryset.filter(environmental_themes__contains=[value])
    
    def filter_has_participation(self, queryset, name, value):
        """Filter projects that have participating schools"""
        if value:
            return queryset.filter(projectparticipation__is_active=True).distinct()
        else:
            return queryset.exclude(projectparticipation__is_active=True)
    
    def filter_min_participants(self, queryset, name, value):
        """Filter projects with minimum number of participants"""
        from django.db.models import Count
        return queryset.annotate(
            participant_count=Count('projectparticipation', filter=Q(projectparticipation__is_active=True))
        ).filter(participant_count__gte=value)


class EnvironmentalImpactFilter(django_filters.FilterSet):
    """Advanced filtering for environmental impacts"""
    
    # Impact type filters
    impact_type = django_filters.ChoiceFilter(choices=EnvironmentalImpact.IMPACT_TYPES)
    
    # Value filters
    min_value = django_filters.NumberFilter(field_name='value', lookup_expr='gte')
    max_value = django_filters.NumberFilter(field_name='value', lookup_expr='lte')
    
    # Date filters
    measured_after = django_filters.DateFilter(field_name='measurement_date', lookup_expr='gte')
    measured_before = django_filters.DateFilter(field_name='measurement_date', lookup_expr='lte')
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    # Related object filters
    project = django_filters.ModelChoiceFilter(queryset=Project.objects.all())
    school = django_filters.ModelChoiceFilter(queryset=School.objects.all())
    project_status = django_filters.CharFilter(field_name='project__status')
    school_country = django_filters.CharFilter(field_name='school__country', lookup_expr='iexact')
    
    # Verification filter
    verified = django_filters.BooleanFilter()
    
    # Date range shortcuts
    this_year = django_filters.BooleanFilter(method='filter_this_year')
    this_month = django_filters.BooleanFilter(method='filter_this_month')
    
    class Meta:
        model = EnvironmentalImpact
        fields = ['impact_type', 'verified', 'project', 'school']
    
    def filter_this_year(self, queryset, name, value):
        """Filter impacts from current year"""
        if value:
            from django.utils import timezone
            current_year = timezone.now().year
            return queryset.filter(measurement_date__year=current_year)
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        """Filter impacts from current month"""
        if value:
            from django.utils import timezone
            now = timezone.now()
            return queryset.filter(
                measurement_date__year=now.year,
                measurement_date__month=now.month
            )
        return queryset


class DonationFilter(django_filters.FilterSet):
    """Advanced filtering for donations"""
    
    # Amount filters
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    
    # Purpose and method filters
    purpose = django_filters.ChoiceFilter(choices=Donation.DONATION_PURPOSES)
    payment_method = django_filters.ChoiceFilter(choices=Donation.PAYMENT_METHODS)
    payment_status = django_filters.CharFilter(lookup_expr='iexact')
    
    # Date filters
    donated_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    donated_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    # Donor filters
    donor_name = django_filters.CharFilter(lookup_expr='icontains')
    donor_email = django_filters.CharFilter(lookup_expr='icontains')
    
    # E-card filters
    send_ecard = django_filters.BooleanFilter()
    has_recipient = django_filters.BooleanFilter(method='filter_has_recipient')
    
    class Meta:
        model = Donation
        fields = ['purpose', 'payment_method', 'payment_status', 'send_ecard']
    
    def filter_has_recipient(self, queryset, name, value):
        """Filter donations that have recipients (honor/memory donations)"""
        if value:
            return queryset.exclude(recipient_name__isnull=True, recipient_name__exact='')
        else:
            return queryset.filter(Q(recipient_name__isnull=True) | Q(recipient_name__exact=''))


class CertificateFilter(django_filters.FilterSet):
    """Advanced filtering for certificates"""
    
    # Type filters
    certificate_type = django_filters.ChoiceFilter(choices=Certificate.CERTIFICATE_TYPES)
    
    # Text searches
    title = django_filters.CharFilter(lookup_expr='icontains')
    recipient_name = django_filters.CharFilter(field_name='recipient__first_name', lookup_expr='icontains')
    
    # Date filters
    issued_after = django_filters.DateFilter(field_name='issued_at', lookup_expr='gte')
    issued_before = django_filters.DateFilter(field_name='issued_at', lookup_expr='lte')
    
    # Related object filters
    project = django_filters.ModelChoiceFilter(queryset=Project.objects.all())
    recipient = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    issued_by = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    
    # Verification
    verification_code = django_filters.CharFilter(lookup_expr='exact')
    
    class Meta:
        model = Certificate
        fields = ['certificate_type', 'project', 'recipient', 'issued_by']


class TeacherProfileFilter(django_filters.FilterSet):
    """Advanced filtering for teacher profiles"""
    
    # Role and status filters
    teacher_role = django_filters.ChoiceFilter(choices=TeacherProfile.TEACHER_ROLES)
    status = django_filters.ChoiceFilter(choices=TeacherProfile.STATUS_CHOICES)
    
    # School filters
    school = django_filters.ModelChoiceFilter(queryset=School.objects.all())
    school_country = django_filters.CharFilter(field_name='school__country', lookup_expr='iexact')
    school_city = django_filters.CharFilter(field_name='school__city', lookup_expr='icontains')
    
    # Subject filters
    assigned_subjects = django_filters.ModelMultipleChoiceFilter(queryset=models.Q())
    has_subjects = django_filters.BooleanFilter(method='filter_has_subjects')
    
    # Class filters
    assigned_classes = django_filters.ModelMultipleChoiceFilter(queryset=models.Q())
    has_classes = django_filters.BooleanFilter(method='filter_has_classes')
    
    class Meta:
        model = TeacherProfile
        fields = ['teacher_role', 'status', 'school']
    
    def filter_has_subjects(self, queryset, name, value):
        """Filter teachers who have assigned subjects"""
        if value:
            return queryset.filter(assigned_subjects__isnull=False).distinct()
        else:
            return queryset.filter(assigned_subjects__isnull=True)
    
    def filter_has_classes(self, queryset, name, value):
        """Filter teachers who have assigned classes"""
        if value:
            return queryset.filter(assigned_classes__isnull=False).distinct()
        else:
            return queryset.filter(assigned_classes__isnull=True)


class StudentProfileFilter(django_filters.FilterSet):
    """Advanced filtering for student profiles"""
    
    # School filters
    school = django_filters.ModelChoiceFilter(queryset=School.objects.all())
    school_country = django_filters.CharFilter(field_name='school__country', lookup_expr='iexact')
    school_city = django_filters.CharFilter(field_name='school__city', lookup_expr='icontains')
    
    # Class filters
    current_class = django_filters.ModelChoiceFilter(queryset=models.Q())
    
    # Enrollment filters
    enrolled_after = django_filters.DateFilter(field_name='enrollment_date', lookup_expr='gte')
    enrolled_before = django_filters.DateFilter(field_name='enrollment_date', lookup_expr='lte')
    
    # Student ID search
    student_id = django_filters.CharFilter(lookup_expr='icontains')
    
    # Parent information
    has_parent_info = django_filters.BooleanFilter(method='filter_has_parent_info')
    
    class Meta:
        model = StudentProfile
        fields = ['school', 'current_class', 'student_id']
    
    def filter_has_parent_info(self, queryset, name, value):
        """Filter students who have parent information"""
        if value:
            return queryset.exclude(
                Q(parent_name__isnull=True) | Q(parent_name__exact='') |
                Q(parent_email__isnull=True) | Q(parent_email__exact='')
            )
        else:
            return queryset.filter(
                Q(parent_name__isnull=True) | Q(parent_name__exact='') |
                Q(parent_email__isnull=True) | Q(parent_email__exact='')
            )


# Custom ordering filters
class CustomOrderingFilter(django_filters.OrderingFilter):
    """Custom ordering filter with predefined choices"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra['choices'] += [
            ('relevance', 'Relevance'),
            ('-relevance', 'Relevance (descending)'),
            ('popularity', 'Popularity'),
            ('-popularity', 'Popularity (descending)'),
        ]


# Utility functions for complex filtering
def filter_by_distance(queryset, latitude, longitude, max_distance_km):
    """Filter objects by distance from a point (requires GeoDjango)"""
    # This would require GeoDjango and PostGIS for full implementation
    # For now, we'll use a simple city/country filter
    return queryset


def filter_by_date_range(queryset, field_name, start_date, end_date):
    """Filter by date range"""
    filters = {}
    if start_date:
        filters[f"{field_name}__gte"] = start_date
    if end_date:
        filters[f"{field_name}__lte"] = end_date
    return queryset.filter(**filters)


def filter_by_keywords(queryset, fields, keywords):
    """Filter by keywords across multiple fields"""
    query = Q()
    for keyword in keywords.split():
        field_query = Q()
        for field in fields:
            field_query |= Q(**{f"{field}__icontains": keyword})
        query &= field_query
    return queryset.filter(query)