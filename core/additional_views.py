"""
Additional API Views for Global Classrooms
Extended functionality including search, reports, analytics, and admin features
"""

import io
import csv
from datetime import datetime, timedelta
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.core.files.storage import default_storage
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination

from .models import (
    User, School, Project, EnvironmentalImpact, Donation, 
    Certificate, SchoolMembership, ProjectParticipation
)
from .serializers import (
    UserSerializer, SchoolSerializer, ProjectSerializer,
    EnvironmentalImpactSerializer, DonationSerializer, CertificateSerializer
)
from .filters import ProjectFilter, SchoolFilter, UserFilter
from .permissions import can_user_access_school
from .utils import (
    StandardResultsSetPagination, calculate_environmental_impact_stats,
    validate_file_extension, compress_image, log_user_activity
)


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_popular_projects(request):
    """Get popular projects based on participation count"""
    projects = Project.objects.filter(
        status='active'
    ).annotate(
        participant_count=Count('projectparticipation', filter=Q(projectparticipation__is_active=True))
    ).order_by('-participant_count')[:10]
    
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_featured_projects(request):
    """Get featured projects"""
    # For now, return active projects with most impact
    projects = Project.objects.filter(
        status='active'
    ).annotate(
        impact_count=Count('impacts', filter=Q(impacts__verified=True))
    ).order_by('-impact_count')[:10]
    
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_featured_schools(request):
    """Get featured schools based on activity"""
    schools = School.objects.filter(
        is_active=True, is_verified=True
    ).annotate(
        project_count=Count('led_projects', filter=Q(led_projects__status='active'))
    ).order_by('-project_count')[:10]
    
    serializer = SchoolSerializer(schools, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_school_members(request, pk):
    """Get members of a specific school"""
    school = get_object_or_404(School, pk=pk)
    
    # Check permissions
    if not can_user_access_school(request.user, school):
        return Response({'error': 'Permission denied'}, status=403)
    
    members = school.memberships.filter(is_active=True)
    
    # Add pagination
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(members, request)
    
    serializer = SchoolMembershipSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_school_projects(request, pk):
    """Get projects for a specific school"""
    school = get_object_or_404(School, pk=pk)
    
    # Get both led and participating projects
    led_projects = school.led_projects.filter(status='active')
    participating = ProjectParticipation.objects.filter(
        school=school, is_active=True
    ).values_list('project', flat=True)
    participating_projects = Project.objects.filter(id__in=participating, status='active')
    
    # Combine and remove duplicates
    all_project_ids = set(led_projects.values_list('id', flat=True)) | set(participating_projects.values_list('id', flat=True))
    all_projects = Project.objects.filter(id__in=all_project_ids)
    
    # Add pagination
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(all_projects, request)
    
    serializer = ProjectSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def verify_certificate(request, verification_code):
    """Verify certificate by verification code"""
    try:
        certificate = Certificate.objects.get(verification_code=verification_code)
        serializer = CertificateSerializer(certificate)
        return Response({
            'valid': True,
            'certificate': serializer.data
        })
    except Certificate.DoesNotExist:
        return Response({
            'valid': False,
            'message': 'Certificate not found'
        }, status=404)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_certificate(request, pk):
    """Download certificate file"""
    certificate = get_object_or_404(Certificate, pk=pk)
    
    # Check if user can access this certificate
    if certificate.recipient != request.user and not request.user.is_staff:
        return Response({'error': 'Permission denied'}, status=403)
    
    # Return certificate file URL or generate PDF
    return Response({
        'download_url': certificate.template_file.url if certificate.template_file else None,
        'certificate': CertificateSerializer(certificate).data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def global_search(request):
    """Global search across all content"""
    query = request.GET.get('q', '')
    if not query:
        return Response({'error': 'Search query required'}, status=400)
    
    # Search across multiple models
    results = {
        'projects': ProjectSerializer(
            Project.objects.filter(
                Q(title__icontains=query) | Q(short_description__icontains=query)
            )[:5], many=True
        ).data,
        'schools': SchoolSerializer(
            School.objects.filter(
                Q(name__icontains=query) | Q(city__icontains=query)
            )[:5], many=True
        ).data,
        'users': UserSerializer(
            User.objects.filter(
                Q(first_name__icontains=query) | Q(last_name__icontains=query)
            )[:5], many=True
        ).data
    }
    
    return Response(results)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def search_projects(request):
    """Advanced project search with filters"""
    query = request.GET.get('q', '')
    projects = Project.objects.filter(status='active')
    
    if query:
        projects = projects.filter(
            Q(title__icontains=query) | Q(short_description__icontains=query)
        )
    
    # Apply filters
    filterset = ProjectFilter(request.GET, queryset=projects)
    if filterset.is_valid():
        projects = filterset.qs
    
    # Paginate results
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(projects, request)
    
    serializer = ProjectSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def search_schools(request):
    """Advanced school search with filters"""
    query = request.GET.get('q', '')
    schools = School.objects.filter(is_active=True)
    
    if query:
        schools = schools.filter(
            Q(name__icontains=query) | Q(city__icontains=query) | Q(country__icontains=query)
        )
    
    # Apply filters
    filterset = SchoolFilter(request.GET, queryset=schools)
    if filterset.is_valid():
        schools = filterset.qs
    
    # Paginate results
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(schools, request)
    
    serializer = SchoolSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_users(request):
    """Advanced user search with filters"""
    query = request.GET.get('q', '')
    users = User.objects.filter(is_active=True)
    
    if query:
        users = users.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query)
        )
    
    # Apply filters
    filterset = UserFilter(request.GET, queryset=users)
    if filterset.is_valid():
        users = filterset.qs
    
    # Paginate results
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(users, request)
    
    serializer = UserSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# =============================================================================
# REPORTING ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def impact_summary_report(request):
    """Generate environmental impact summary report"""
    # Get date range from query params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    impacts = EnvironmentalImpact.objects.filter(verified=True)
    
    if start_date:
        impacts = impacts.filter(measurement_date__gte=start_date)
    if end_date:
        impacts = impacts.filter(measurement_date__lte=end_date)
    
    # Calculate statistics
    stats = calculate_environmental_impact_stats(impacts)
    
    # Group by impact type
    impact_breakdown = {}
    for impact_type, _ in EnvironmentalImpact.IMPACT_TYPES:
        type_impacts = impacts.filter(impact_type=impact_type)
        impact_breakdown[impact_type] = {
            'total_value': type_impacts.aggregate(Sum('value'))['value__sum'] or 0,
            'count': type_impacts.count(),
            'schools': type_impacts.values('school').distinct().count(),
            'projects': type_impacts.values('project').distinct().count()
        }
    
    return Response({
        'summary': stats,
        'breakdown': impact_breakdown,
        'date_range': {
            'start_date': start_date,
            'end_date': end_date
        },
        'total_records': impacts.count()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def school_activity_report(request):
    """Generate school activity report"""
    schools = School.objects.filter(is_active=True).annotate(
        member_count=Count('memberships', filter=Q(memberships__is_active=True)),
        project_count=Count('led_projects', filter=Q(led_projects__status='active')),
        impact_count=Count('impacts', filter=Q(impacts__verified=True))
    )
    
    # Filter by country if specified
    country = request.GET.get('country')
    if country:
        schools = schools.filter(country__iexact=country)
    
    school_data = []
    for school in schools:
        school_data.append({
            'id': school.id,
            'name': school.name,
            'city': school.city,
            'country': school.country,
            'member_count': school.member_count,
            'project_count': school.project_count,
            'impact_count': school.impact_count,
            'created_at': school.created_at
        })
    
    return Response({
        'schools': school_data,
        'total_schools': schools.count(),
        'total_members': sum(s['member_count'] for s in school_data),
        'total_projects': sum(s['project_count'] for s in school_data)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def project_progress_report(request):
    """Generate project progress report"""
    projects = Project.objects.all().annotate(
        participant_count=Count('projectparticipation', filter=Q(projectparticipation__is_active=True)),
        impact_count=Count('impacts', filter=Q(impacts__verified=True))
    )
    
    # Filter by status if specified
    project_status = request.GET.get('status')
    if project_status:
        projects = projects.filter(status=project_status)
    
    project_data = []
    for project in projects:
        days_remaining = (project.end_date - timezone.now().date()).days if project.end_date > timezone.now().date() else 0
        
        project_data.append({
            'id': project.id,
            'title': project.title,
            'status': project.status,
            'start_date': project.start_date,
            'end_date': project.end_date,
            'days_remaining': days_remaining,
            'participant_count': project.participant_count,
            'impact_count': project.impact_count,
            'lead_school': project.lead_school.name,
            'created_at': project.created_at
        })
    
    return Response({
        'projects': project_data,
        'total_projects': projects.count(),
        'active_projects': projects.filter(status='active').count(),
        'completed_projects': projects.filter(status='completed').count()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def donation_summary_report(request):
    """Generate donation summary report"""
    donations = Donation.objects.filter(payment_status='completed')
    
    # Get date range from query params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        donations = donations.filter(created_at__date__gte=start_date)
    if end_date:
        donations = donations.filter(created_at__date__lte=end_date)
    
    # Calculate statistics
    total_amount = donations.aggregate(Sum('amount'))['amount__sum'] or 0
    average_amount = donations.aggregate(Avg('amount'))['amount__avg'] or 0
    
    # Group by purpose
    purpose_breakdown = {}
    for purpose, _ in Donation.DONATION_PURPOSES:
        purpose_donations = donations.filter(purpose=purpose)
        purpose_breakdown[purpose] = {
            'count': purpose_donations.count(),
            'total_amount': purpose_donations.aggregate(Sum('amount'))['amount__sum'] or 0
        }
    
    return Response({
        'summary': {
            'total_donations': donations.count(),
            'total_amount': float(total_amount),
            'average_amount': float(average_amount)
        },
        'breakdown': purpose_breakdown,
        'date_range': {
            'start_date': start_date,
            'end_date': end_date
        }
    })


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def project_trends(request):
    """Get project creation trends over time"""
    # Get projects from last 12 months
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)
    
    projects = Project.objects.filter(created_at__date__range=[start_date, end_date])
    
    # Group by month
    monthly_data = {}
    for project in projects:
        month_key = project.created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {'count': 0, 'active': 0}
        monthly_data[month_key]['count'] += 1
        if project.status == 'active':
            monthly_data[month_key]['active'] += 1
    
    return Response({
        'monthly_trends': monthly_data,
        'total_projects': projects.count(),
        'date_range': {
            'start_date': start_date,
            'end_date': end_date
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def impact_trends(request):
    """Get environmental impact trends over time"""
    # Get impacts from last 12 months
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)
    
    impacts = EnvironmentalImpact.objects.filter(
        verified=True,
        measurement_date__range=[start_date, end_date]
    )
    
    # Group by month and impact type
    monthly_data = {}
    for impact in impacts:
        month_key = impact.measurement_date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {}
        
        impact_type = impact.impact_type
        if impact_type not in monthly_data[month_key]:
            monthly_data[month_key][impact_type] = 0
        
        monthly_data[month_key][impact_type] += float(impact.value)
    
    return Response({
        'monthly_trends': monthly_data,
        'total_impacts': impacts.count(),
        'date_range': {
            'start_date': start_date,
            'end_date': end_date
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def school_growth(request):
    """Get school registration growth over time"""
    # Get schools from last 12 months
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)
    
    schools = School.objects.filter(created_at__date__range=[start_date, end_date])
    
    # Group by month
    monthly_data = {}
    cumulative_count = School.objects.filter(created_at__date__lt=start_date).count()
    
    for school in schools.order_by('created_at'):
        month_key = school.created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {'new_schools': 0, 'cumulative': cumulative_count}
        monthly_data[month_key]['new_schools'] += 1
        cumulative_count += 1
        monthly_data[month_key]['cumulative'] = cumulative_count
    
    return Response({
        'monthly_growth': monthly_data,
        'total_new_schools': schools.count(),
        'date_range': {
            'start_date': start_date,
            'end_date': end_date
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_engagement(request):
    """Get user engagement metrics"""
    # Get users from last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Basic engagement metrics
    total_users = User.objects.filter(is_active=True).count()
    new_users = User.objects.filter(date_joined__date__range=[start_date, end_date]).count()
    
    # User roles distribution
    role_distribution = {}
    for role, _ in User.USER_ROLES:
        role_distribution[role] = User.objects.filter(role=role, is_active=True).count()
    
    return Response({
        'total_users': total_users,
        'new_users_30_days': new_users,
        'role_distribution': role_distribution,
        'date_range': {
            'start_date': start_date,
            'end_date': end_date
        }
    })


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_dashboard_stats(request):
    """Get comprehensive admin dashboard statistics"""
    stats = {
        'users': {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'by_role': {role: User.objects.filter(role=role).count() for role, _ in User.USER_ROLES}
        },
        'schools': {
            'total': School.objects.count(),
            'active': School.objects.filter(is_active=True).count(),
            'verified': School.objects.filter(is_verified=True).count(),
            'pending_verification': School.objects.filter(is_verified=False, is_active=True).count()
        },
        'projects': {
            'total': Project.objects.count(),
            'by_status': {status: Project.objects.filter(status=status).count() for status, _ in Project.STATUS_CHOICES}
        },
        'impacts': {
            'total': EnvironmentalImpact.objects.count(),
            'verified': EnvironmentalImpact.objects.filter(verified=True).count(),
            'pending_verification': EnvironmentalImpact.objects.filter(verified=False).count()
        },
        'donations': {
            'total_count': Donation.objects.count(),
            'total_amount': float(Donation.objects.filter(payment_status='completed').aggregate(Sum('amount'))['amount__sum'] or 0),
            'completed': Donation.objects.filter(payment_status='completed').count()
        }
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def verify_school(request, school_id):
    """Verify a school"""
    school = get_object_or_404(School, id=school_id)
    school.is_verified = True
    school.save()
    
    log_user_activity(request.user, 'school_verified', f'School: {school.name}')
    
    return Response({'message': f'School {school.name} has been verified'})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def verify_impact(request, impact_id):
    """Verify an environmental impact"""
    impact = get_object_or_404(EnvironmentalImpact, id=impact_id)
    impact.verified = True
    impact.save()
    
    log_user_activity(request.user, 'impact_verified', f'Impact: {impact.impact_type} - {impact.value}')
    
    return Response({'message': 'Environmental impact has been verified'})


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAdminUser])
def manage_featured_content(request):
    """Manage featured content"""
    if request.method == 'GET':
        # Return current featured content
        featured_projects = Project.objects.filter(is_featured=True)
        featured_schools = School.objects.filter(is_featured=True)
        
        return Response({
            'featured_projects': ProjectSerializer(featured_projects, many=True).data,
            'featured_schools': SchoolSerializer(featured_schools, many=True).data
        })
    
    elif request.method == 'POST':
        # Update featured content
        project_ids = request.data.get('project_ids', [])
        school_ids = request.data.get('school_ids', [])
        
        # Clear current featured status
        Project.objects.filter(is_featured=True).update(is_featured=False)
        School.objects.filter(is_featured=True).update(is_featured=False)
        
        # Set new featured content
        if project_ids:
            Project.objects.filter(id__in=project_ids).update(is_featured=True)
        if school_ids:
            School.objects.filter(id__in=school_ids).update(is_featured=True)
        
        return Response({'message': 'Featured content updated successfully'})


# =============================================================================
# FILE UPLOAD ENDPOINTS
# =============================================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_image(request):
    """Upload and process image files"""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    
    # Validate file extension
    if not validate_file_extension(file.name, settings.ALLOWED_IMAGE_EXTENSIONS):
        return Response({'error': 'Invalid file type'}, status=400)
    
    # Validate file size
    if file.size > settings.MAX_IMAGE_SIZE:
        return Response({'error': 'File too large'}, status=400)
    
    try:
        # Compress image
        compressed_file = compress_image(file)
        
        # Save file
        filename = f"uploads/images/{timezone.now().strftime('%Y/%m/%d')}/{file.name}"
        path = default_storage.save(filename, compressed_file)
        
        return Response({
            'message': 'Image uploaded successfully',
            'url': default_storage.url(path),
            'path': path
        })
    
    except Exception as e:
        return Response({'error': 'Failed to upload image'}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_document(request):
    """Upload document files"""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    
    # Validate file extension
    if not validate_file_extension(file.name, settings.ALLOWED_DOCUMENT_EXTENSIONS):
        return Response({'error': 'Invalid file type'}, status=400)
    
    # Validate file size
    if file.size > settings.MAX_DOCUMENT_SIZE:
        return Response({'error': 'File too large'}, status=400)
    
    try:
        # Save file
        filename = f"uploads/documents/{timezone.now().strftime('%Y/%m/%d')}/{file.name}"
        path = default_storage.save(filename, file)
        
        return Response({
            'message': 'Document uploaded successfully',
            'url': default_storage.url(path),
            'path': path
        })
    
    except Exception as e:
        return Response({'error': 'Failed to upload document'}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
@parser_classes([MultiPartParser, FormParser])
def bulk_import_data(request):
    """Bulk import data from CSV files"""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    data_type = request.data.get('type', '')
    
    if not file.name.endswith('.csv'):
        return Response({'error': 'Only CSV files are supported'}, status=400)
    
    try:
        # Read CSV file
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        
        imported_count = 0
        errors = []
        
        # Process based on data type
        if data_type == 'schools':
            for row in reader:
                try:
                    # Create school from CSV data
                    # Implementation depends on CSV structure
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Row {reader.line_num}: {str(e)}")
        
        elif data_type == 'users':
            for row in reader:
                try:
                    # Create user from CSV data
                    # Implementation depends on CSV structure
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Row {reader.line_num}: {str(e)}")
        
        return Response({
            'message': f'Imported {imported_count} records',
            'imported_count': imported_count,
            'errors': errors
        })
    
    except Exception as e:
        return Response({'error': 'Failed to process file'}, status=500)


# =============================================================================
# NOTIFICATION ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_notifications(request):
    """Get user notifications (placeholder)"""
    # This would typically integrate with a notification system
    notifications = [
        {
            'id': 1,
            'title': 'Welcome to Global Classrooms',
            'message': 'Thank you for joining our environmental education platform!',
            'type': 'welcome',
            'read': False,
            'created_at': timezone.now()
        }
    ]
    
    return Response({'notifications': notifications})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notifications_read(request):
    """Mark notifications as read"""
    notification_ids = request.data.get('notification_ids', [])
    
    # Implementation would mark notifications as read
    
    return Response({'message': 'Notifications marked as read'})