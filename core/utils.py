"""
Utility functions and helpers for Global Classrooms API
"""

import os
import uuid
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.pagination import PageNumberPagination

from PIL import Image
import io

from eth_account.messages import encode_defunct
from eth_account import Account

from .models import WalletNonce

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM EXCEPTION HANDLER
# =============================================================================

def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error response format
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'error': True,
            'message': 'An error occurred',
            'details': response.data,
            'status_code': response.status_code,
            'timestamp': timezone.now().isoformat()
        }
        
        # Customize messages for common errors
        if response.status_code == 400:
            custom_response_data['message'] = 'Bad request - please check your input'
        elif response.status_code == 401:
            custom_response_data['message'] = 'Authentication required'
        elif response.status_code == 403:
            custom_response_data['message'] = 'Permission denied'
        elif response.status_code == 404:
            custom_response_data['message'] = 'Resource not found'
        elif response.status_code == 405:
            custom_response_data['message'] = 'Method not allowed'
        elif response.status_code == 429:
            custom_response_data['message'] = 'Too many requests'
        elif response.status_code >= 500:
            custom_response_data['message'] = 'Internal server error'
            # Log server errors
            logger.error(f"Server error: {exc}", exc_info=True)
        
        response.data = custom_response_data
    
    return response


# =============================================================================
# PAGINATION CLASSES
# =============================================================================

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'pagination': {
                'links': {
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link()
                },
                'count': self.page.paginator.count,
                'page_size': self.page_size,
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
            },
            'results': data
        })


class LargeResultsSetPagination(PageNumberPagination):
    """Pagination for large datasets"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


# =============================================================================
# FILE HANDLING UTILITIES
# =============================================================================

def generate_unique_filename(instance, filename):
    """Generate unique filename for uploads"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return filename


def validate_file_extension(filename, allowed_extensions):
    """Validate file extension"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def validate_file_size(file, max_size):
    """Validate file size"""
    return file.size <= max_size


def compress_image(image_file, quality=85, max_width=1920, max_height=1080):
    """Compress and resize image"""
    try:
        # Open the image
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Calculate new dimensions
        width, height = img.size
        if width > max_width or height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save compressed image
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return ContentFile(output.read())
    
    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        return image_file


def safe_delete_file(file_path):
    """Safely delete file from storage"""
    try:
        if default_storage.exists(file_path):
            default_storage.delete(file_path)
            return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
    return False


# =============================================================================
# EMAIL UTILITIES
# =============================================================================

def send_welcome_email(user):
    """Send welcome email to new user"""
    try:
        subject = 'Welcome to Global Classrooms!'
        
        context = {
            'user': user,
            'login_url': f"{settings.FRONTEND_URL}/login" if hasattr(settings, 'FRONTEND_URL') else '#'
        }
        
        html_message = render_to_string('emails/welcome.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Welcome email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending welcome email to {user.email}: {e}")
        return False


def send_password_reset_email(user, token):
    """Send password reset email"""
    try:
        subject = 'Reset Your Password - Global Classrooms'
        
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uidb64}/{token}/" if hasattr(settings, 'FRONTEND_URL') else '#'
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'expiry_hours': 24
        }
        
        html_message = render_to_string('emails/password_reset.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending password reset email to {user.email}: {e}")
        return False


def send_project_invitation_email(user, project, school):
    """Send project collaboration invitation email"""
    try:
        subject = f'Invitation to Join Project: {project.title}'
        
        context = {
            'user': user,
            'project': project,
            'school': school,
            'project_url': f"{settings.FRONTEND_URL}/projects/{project.id}/" if hasattr(settings, 'FRONTEND_URL') else '#'
        }
        
        html_message = render_to_string('emails/project_invitation.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Project invitation email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending project invitation email to {user.email}: {e}")
        return False


# =============================================================================
# STATISTICS UTILITIES
# =============================================================================

def calculate_environmental_impact_stats(queryset=None):
    """Calculate environmental impact statistics"""
    from .models import EnvironmentalImpact
    
    if queryset is None:
        impacts = EnvironmentalImpact.objects.filter(verified=True)
    else:
        impacts = queryset.filter(verified=True)
    
    stats = {
        'total_trees_planted': impacts.filter(
            impact_type='trees_planted'
        ).aggregate(Sum('value'))['value__sum'] or 0,
        
        'total_students_engaged': impacts.filter(
            impact_type='students_engaged'
        ).aggregate(Sum('value'))['value__sum'] or 0,
        
        'total_waste_recycled': impacts.filter(
            impact_type='waste_recycled'
        ).aggregate(Sum('value'))['value__sum'] or 0,
        
        'total_water_saved': impacts.filter(
            impact_type='water_saved'
        ).aggregate(Sum('value'))['value__sum'] or 0,
        
        'total_carbon_reduced': impacts.filter(
            impact_type='carbon_reduced'
        ).aggregate(Sum('value'))['value__sum'] or 0,
        
        'total_energy_saved': impacts.filter(
            impact_type='energy_saved'
        ).aggregate(Sum('value'))['value__sum'] or 0,
    }
    
    return stats


def calculate_school_stats(school):
    """Calculate statistics for a specific school"""
    stats = {
        'member_count': school.memberships.filter(is_active=True).count(),
        'teacher_count': school.teachers.filter(status='active').count(),
        'student_count': school.students.count(),
        'led_projects': school.led_projects.filter(status='active').count(),
        'participating_projects': school.projects.filter(status='active').count(),
    }
    
    # Environmental impact stats for this school
    impact_stats = calculate_environmental_impact_stats(school.impacts)
    stats.update(impact_stats)
    
    return stats


def calculate_project_stats(project):
    """Calculate statistics for a specific project"""
    stats = {
        'participating_schools': project.participating_schools.filter(
            projectparticipation__is_active=True
        ).count(),
        'duration_days': (project.end_date - project.start_date).days,
        'is_active': project.status == 'active',
        'has_ended': project.end_date < timezone.now().date(),
    }
    
    # Environmental impact stats for this project
    impact_stats = calculate_environmental_impact_stats(project.impacts)
    stats.update(impact_stats)
    
    return stats


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_environmental_theme(theme):
    """Validate environmental theme"""
    from .models import Project
    valid_themes = [choice[0] for choice in Project.ENVIRONMENTAL_THEMES]
    return theme in valid_themes


def validate_project_dates(start_date, end_date):
    """Validate project start and end dates"""
    errors = []
    
    # Check if start date is in the future (allowing today)
    if start_date < timezone.now().date():
        errors.append("Start date cannot be in the past")
    
    # Check if end date is after start date
    if end_date <= start_date:
        errors.append("End date must be after start date")
    
    # Check if project duration is reasonable (not more than 5 years)
    if (end_date - start_date).days > 1825:  # 5 years
        errors.append("Project duration cannot exceed 5 years")
    
    return errors


def validate_impact_value(impact_type, value):
    """Validate environmental impact value"""
    errors = []
    
    # Check if value is positive
    if value <= 0:
        errors.append("Impact value must be positive")
    
    # Check reasonable limits for different impact types
    limits = {
        'trees_planted': 1000000,  # 1 million trees max
        'students_engaged': 100000,  # 100k students max
        'waste_recycled': 1000000,  # 1 million kg max
        'water_saved': 10000000,  # 10 million liters max
        'carbon_reduced': 1000000,  # 1 million kg CO2 max
        'energy_saved': 1000000,  # 1 million kWh max
    }
    
    if impact_type in limits and value > limits[impact_type]:
        errors.append(f"Value seems unreasonably high for {impact_type}")
    
    return errors


def verify_wallet_signature(wallet_address: str, message: str, signature: str, purpose: str):
    """
    Verify the `message`:
      - Matches the expected format with the current nonce for wallet_address
      - Has a valid Ethereum signature from wallet_address

    `purpose` is a string ("Login" or "Register") to distinguish message formats.
    """

    wallet_address = wallet_address.lower()

    # 1) Load nonce record
    try:
        nonce_obj = WalletNonce.objects.get(wallet_address=wallet_address)
    except WalletNonce.DoesNotExist:
        return False, Response({'error': 'Nonce not found for wallet'}, status=status.HTTP_400_BAD_REQUEST)

    # 2) Check expiry
    if nonce_obj.created_at < timezone.now() - timedelta(minutes=10):
        return False, Response({'error': 'Nonce expired'}, status=status.HTTP_400_BAD_REQUEST)

    expected_nonce = nonce_obj.nonce

    # 3) Build expected message
    expected_message = f"{purpose} to Global Classrooms with this wallet\n\nNonce: {expected_nonce}"

    if message != expected_message:
        return False, Response({'error': 'Invalid nonce or message'}, status=status.HTTP_400_BAD_REQUEST)

    # 4) Verify signature
    try:
        msg_hash = encode_defunct(text=message)
        recovered = Account.recover_message(msg_hash, signature=signature)
        if recovered.lower() != wallet_address:
            return False, Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception:
        return False, Response({'error': 'Invalid signature format'}, status=status.HTTP_400_BAD_REQUEST)

    # 5) Invalidate nonce (one-time use)
    nonce_obj.delete()

    return True, None


# =============================================================================
# SEARCH UTILITIES
# =============================================================================

def build_search_query(search_terms, fields):
    """Build search query for multiple fields"""
    query = Q()
    
    for term in search_terms.split():
        term_query = Q()
        for field in fields:
            term_query |= Q(**{f"{field}__icontains": term})
        query &= term_query
    
    return query


def get_popular_projects(limit=10):
    """Get popular projects based on participation"""
    from .models import Project
    
    return Project.objects.filter(
        status='active'
    ).annotate(
        participant_count=Count('projectparticipation', filter=Q(projectparticipation__is_active=True))
    ).order_by('-participant_count')[:limit]


def get_featured_schools(limit=10):
    """Get featured schools based on activity"""
    from .models import School
    
    return School.objects.filter(
        is_active=True, is_verified=True
    ).annotate(
        project_count=Count('led_projects', filter=Q(led_projects__status='active'))
    ).order_by('-project_count')[:limit]


# =============================================================================
# DATA TRANSFORMATION UTILITIES
# =============================================================================

def serialize_impact_data_for_charts(impacts):
    """Transform impact data for frontend charts"""
    chart_data = {}
    
    for impact in impacts:
        impact_type = impact.impact_type
        if impact_type not in chart_data:
            chart_data[impact_type] = {
                'label': dict(EnvironmentalImpact.IMPACT_TYPES).get(impact_type, impact_type),
                'data': [],
                'total': 0
            }
        
        chart_data[impact_type]['data'].append({
            'date': impact.measurement_date.isoformat(),
            'value': float(impact.value),
            'school': impact.school.name,
            'project': impact.project.title
        })
        chart_data[impact_type]['total'] += float(impact.value)
    
    return chart_data


def prepare_dashboard_data(user):
    """Prepare dashboard data based on user role"""
    from .models import School, Project, EnvironmentalImpact
    
    data = {
        'user_info': {
            'name': user.get_full_name(),
            'role': user.role,
            'email': user.email
        }
    }
    
    if user.role == 'super_admin':
        # Global statistics for super admin
        data.update({
            'total_schools': School.objects.filter(is_active=True).count(),
            'total_projects': Project.objects.count(),
            'active_projects': Project.objects.filter(status='active').count(),
            'global_impact': calculate_environmental_impact_stats()
        })
    
    elif user.role == 'school_admin':
        # School-specific data for school admin
        schools = user.managed_schools.filter(is_active=True)
        if schools.exists():
            school = schools.first()
            data.update({
                'school_info': {
                    'id': school.id,
                    'name': school.name,
                    'member_count': school.memberships.filter(is_active=True).count()
                },
                'school_stats': calculate_school_stats(school)
            })
    
    elif user.role in ['teacher', 'student']:
        # School memberships for teachers and students
        memberships = user.school_memberships.filter(is_active=True)
        data['schools'] = [
            {
                'id': membership.school.id,
                'name': membership.school.name,
                'role': user.role
            }
            for membership in memberships
        ]
    
    return data


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def log_user_activity(user, action, details=None):
    """Log user activity for auditing"""
    logger.info(
        f"User Activity - User: {user.username} ({user.id}), "
        f"Action: {action}, Details: {details or 'None'}"
    )


def log_api_error(request, error, details=None):
    """Log API errors with context"""
    logger.error(
        f"API Error - Method: {request.method}, "
        f"Path: {request.path}, Error: {error}, "
        f"User: {getattr(request.user, 'username', 'Anonymous')}, "
        f"Details: {details or 'None'}"
    )


# =============================================================================
# CACHE UTILITIES
# =============================================================================

def get_cache_key(prefix, *args):
    """Generate cache key"""
    return f"{prefix}:{'_'.join(str(arg) for arg in args)}"


def cache_stats(key, data, timeout=300):
    """Cache statistics data"""
    from django.core.cache import cache
    cache.set(key, data, timeout)


def get_cached_stats(key):
    """Get cached statistics"""
    from django.core.cache import cache
    return cache.get(key)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_currency(amount, currency='USD'):
    """Format currency amount"""
    return f"{currency} {amount:,.2f}"


def format_large_number(number):
    """Format large numbers with K, M, B suffixes"""
    if number >= 1000000000:
        return f"{number/1000000000:.1f}B"
    elif number >= 1000000:
        return f"{number/1000000:.1f}M"
    elif number >= 1000:
        return f"{number/1000:.1f}K"
    else:
        return str(int(number))


def slugify_filename(filename):
    """Create URL-safe filename"""
    import re
    name, ext = os.path.splitext(filename)
    name = re.sub(r'[^a-zA-Z0-9\-_]', '_', name)
    return f"{name}{ext}".lower()


def generate_verification_code():
    """Generate verification code for certificates"""
    return str(uuid.uuid4()).replace('-', '').upper()[:8]