"""
API Views for Global Classrooms
Handles all REST API endpoints for the application
"""

from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.mail import send_mail
import random

from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import (
    User, School, Subject, Class, TeacherProfile, StudentProfile,
    Project, ProjectParticipation, EnvironmentalImpact, Donation,
    Certificate, SchoolMembership, EmailLoginOTP
)
from .serializers import (
    UserRegistrationSerializer, UserSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, SchoolSerializer, SchoolCreateSerializer,
    SchoolMembershipSerializer, SubjectSerializer, ClassSerializer,
    TeacherProfileSerializer, StudentProfileSerializer, ProjectSerializer,
    ProjectCreateSerializer, ProjectParticipationSerializer,
    EnvironmentalImpactSerializer, ImpactStatsSerializer,
    DonationSerializer, DonationCreateSerializer, CertificateSerializer,
    DashboardStatsSerializer, SchoolDashboardSerializer
)
from .permissions import IsOwnerOrReadOnly, IsSchoolAdminOrReadOnly, IsTeacherOrReadOnly
from .filters import ProjectFilter, SchoolFilter, EnvironmentalImpactFilter
from rest_framework.permissions import AllowAny


# =============================================================================
# AUTHENTICATION & LOGIN VIEWS (Grouped at the top for clarity)
# =============================================================================

class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view that returns user data with tokens"""
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get('username')
            user = User.objects.get(username=username)
            user_data = UserSerializer(user).data
            response.data['user'] = user_data
        return response

class UserRegistrationView(CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

class WalletLoginView(APIView):
    """Login using wallet address"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        wallet_address = request.data.get('wallet_address')
        if not wallet_address:
            return Response({'error': 'wallet_address is required'}, status=400)
        try:
            user = User.objects.get(wallet_address=wallet_address)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        if not user.is_active:
            return Response({'error': 'User is inactive'}, status=403)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

class GoogleLoginView(APIView):
    """Login using Google account ID"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        google_account_id = request.data.get('google_account_id')
        if not google_account_id:
            return Response({'error': 'google_account_id is required'}, status=400)
        try:
            user = User.objects.get(google_account_id=google_account_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        if not user.is_active:
            return Response({'error': 'User is inactive'}, status=403)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

class EmailLoginRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=400)
        code = str(random.randint(100000, 999999))
        EmailLoginOTP.objects.create(email=email, code=code)
        send_mail(
            'Your Global Classrooms Login Code',
            f'Your login code is: {code}',
            'no-reply@globalclassrooms.org',
            [email],
        )
        return Response({'message': 'A login code has been sent to your email.'})

class EmailLoginVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        if not email or not code:
            return Response({'error': 'Email and code are required.'}, status=400)
        try:
            otp = EmailLoginOTP.objects.filter(email=email, code=code, is_used=False).latest('created_at')
        except EmailLoginOTP.DoesNotExist:
            return Response({'error': 'Invalid code.'}, status=400)
        if otp.is_expired():
            return Response({'error': 'Code expired.'}, status=400)
        otp.is_used = True
        otp.save()
        user, created = User.objects.get_or_create(email=email, defaults={'username': email.split('@')[0]})
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

class UserProfileView(RetrieveUpdateAPIView):
    """User profile view for getting and updating profile"""
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_object(self):
        return self.request.user
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserSerializer
        return UserUpdateSerializer

class PasswordChangeView(APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'No user with this email.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.check_password(password):
            return Response({'error': 'Invalid password.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({'error': 'User is inactive.'}, status=status.HTTP_403_FORBIDDEN)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


# =============================================================================
# USER VIEWSET
# =============================================================================

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'gender', 'country', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['date_joined', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]


# =============================================================================
# SCHOOL VIEWSETS
# =============================================================================

class SchoolViewSet(viewsets.ModelViewSet):
    """ViewSet for managing schools"""
    queryset = School.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SchoolFilter
    search_fields = ['name', 'city', 'country', 'principal_name']
    ordering_fields = ['name', 'created_at', 'number_of_students']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SchoolCreateSerializer
        return SchoolSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsSchoolAdminOrReadOnly]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """Get school dashboard data"""
        school = self.get_object()
        
        # Check if user has access to this school
        if not school.memberships.filter(user=request.user, is_active=True).exists():
            if request.user != school.admin and not request.user.is_staff:
                return Response(
                    {'error': 'You do not have access to this school'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Gather dashboard data
        member_count = school.memberships.filter(is_active=True).count()
        project_count = school.led_projects.filter(status='active').count()
        
        # Impact statistics
        impacts = school.impacts.filter(verified=True)
        total_impact = {
            'total_trees_planted': impacts.filter(impact_type='trees_planted').aggregate(Sum('value'))['value__sum'] or 0,
            'total_students_engaged': impacts.filter(impact_type='students_engaged').aggregate(Sum('value'))['value__sum'] or 0,
            'total_waste_recycled': impacts.filter(impact_type='waste_recycled').aggregate(Sum('value'))['value__sum'] or 0,
            'total_water_saved': impacts.filter(impact_type='water_saved').aggregate(Sum('value'))['value__sum'] or 0,
            'total_carbon_reduced': impacts.filter(impact_type='carbon_reduced').aggregate(Sum('value'))['value__sum'] or 0,
            'active_projects': project_count,
            'participating_schools': school.projects.filter(status='active').count()
        }
        
        # Recent projects and impacts
        recent_projects = school.led_projects.filter(status='active')[:5]
        recent_impacts = school.impacts.order_by('-created_at')[:10]
        
        data = {
            'school_info': SchoolSerializer(school).data,
            'member_count': member_count,
            'project_count': project_count,
            'total_impact': total_impact,
            'recent_projects': ProjectSerializer(recent_projects, many=True).data,
            'recent_impacts': EnvironmentalImpactSerializer(recent_impacts, many=True).data
        }
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a school"""
        school = self.get_object()
        user = request.user
        
        membership, created = SchoolMembership.objects.get_or_create(
            user=user, 
            school=school,
            defaults={'is_active': True}
        )
        
        if not created:
            if membership.is_active:
                return Response(
                    {'message': 'You are already a member of this school'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                membership.is_active = True
                membership.save()
        
        return Response({'message': 'Successfully joined the school'})


class SchoolMembershipViewSet(viewsets.ModelViewSet):
    """ViewSet for managing school memberships"""
    queryset = SchoolMembership.objects.all()
    serializer_class = SchoolMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['school', 'is_active']
    
    def get_queryset(self):
        # Users can only see memberships for schools they're admin of or their own memberships
        user = self.request.user
        if user.is_staff:
            return SchoolMembership.objects.all()
        
        return SchoolMembership.objects.filter(
            Q(school__admin=user) | Q(user=user)
        )


# =============================================================================
# SUBJECT & CLASS VIEWSETS
# =============================================================================

class SubjectViewSet(viewsets.ModelViewSet):
    """ViewSet for managing subjects"""
    queryset = Subject.objects.filter(is_active=True)
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ClassViewSet(viewsets.ModelViewSet):
    """ViewSet for managing classes"""
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['school']
    search_fields = ['name']


# =============================================================================
# PROFILE VIEWSETS
# =============================================================================

class TeacherProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing teacher profiles"""
    queryset = TeacherProfile.objects.all()
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsTeacherOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['school', 'teacher_role', 'status']
    
    def get_queryset(self):
        # Teachers can only see profiles from their schools
        user = self.request.user
        if user.is_staff:
            return TeacherProfile.objects.all()
        
        user_schools = user.school_memberships.filter(is_active=True).values_list('school', flat=True)
        return TeacherProfile.objects.filter(school__in=user_schools)


class StudentProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing student profiles"""
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsTeacherOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['school', 'current_class']
    
    def get_queryset(self):
        # Users can only see student profiles from their schools
        user = self.request.user
        if user.is_staff:
            return StudentProfile.objects.all()
        
        user_schools = user.school_memberships.filter(is_active=True).values_list('school', flat=True)
        return StudentProfile.objects.filter(school__in=user_schools)


# =============================================================================
# PROJECT VIEWSETS
# =============================================================================

class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for managing projects"""
    queryset = Project.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ['title', 'short_description', 'lead_school__name']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'title']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectCreateSerializer
        return ProjectSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrReadOnly]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a project"""
        project = self.get_object()
        user = request.user
        
        # Check if user has a school membership
        school_memberships = user.school_memberships.filter(is_active=True)
        if not school_memberships.exists():
            return Response(
                {'error': 'You must be a member of a school to join projects'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For now, use the first active school membership
        school = school_memberships.first().school
        
        participation, created = ProjectParticipation.objects.get_or_create(
            project=project,
            school=school,
            defaults={'is_active': True}
        )
        
        if not created:
            if participation.is_active:
                return Response(
                    {'message': 'Your school is already participating in this project'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                participation.is_active = True
                participation.save()
        
        return Response({'message': 'Successfully joined the project'})
    
    @action(detail=True, methods=['get'])
    def impacts(self, request, pk=None):
        """Get project impacts"""
        project = self.get_object()
        impacts = project.impacts.filter(verified=True)
        serializer = EnvironmentalImpactSerializer(impacts, many=True)
        return Response(serializer.data)


class ProjectParticipationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing project participation"""
    queryset = ProjectParticipation.objects.all()
    serializer_class = ProjectParticipationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project', 'school', 'is_active']


# =============================================================================
# ENVIRONMENTAL IMPACT VIEWSETS
# =============================================================================

class EnvironmentalImpactViewSet(viewsets.ModelViewSet):
    """ViewSet for managing environmental impacts"""
    queryset = EnvironmentalImpact.objects.all()
    serializer_class = EnvironmentalImpactSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = EnvironmentalImpactFilter
    ordering_fields = ['measurement_date', 'created_at', 'value']
    ordering = ['-measurement_date']
    
    def get_queryset(self):
        # Users can only see impacts from their schools
        user = self.request.user
        if user.is_staff:
            return EnvironmentalImpact.objects.all()
        
        user_schools = user.school_memberships.filter(is_active=True).values_list('school', flat=True)
        return EnvironmentalImpact.objects.filter(school__in=user_schools)


# =============================================================================
# DONATION VIEWSETS
# =============================================================================

class DonationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing donations"""
    queryset = Donation.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['purpose', 'payment_status', 'payment_method']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DonationCreateSerializer
        return DonationSerializer
    
    def get_queryset(self):
        # Only staff can see all donations
        if self.request.user.is_staff:
            return Donation.objects.all()
        
        # Anonymous users can only see successful donations (for transparency)
        return Donation.objects.filter(payment_status='completed')


# =============================================================================
# CERTIFICATE VIEWSETS
# =============================================================================

class CertificateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing certificates"""
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['certificate_type', 'project', 'recipient']
    ordering_fields = ['issued_at']
    ordering = ['-issued_at']
    
    def get_queryset(self):
        # Users can only see their own certificates or certificates they issued
        user = self.request.user
        if user.is_staff:
            return Certificate.objects.all()
        
        return Certificate.objects.filter(
            Q(recipient=user) | Q(issued_by=user)
        )
    
    @action(detail=True, methods=['get'])
    def verify(self, request, pk=None):
        """Verify certificate by verification code"""
        certificate = self.get_object()
        return Response({
            'is_valid': True,
            'certificate': CertificateSerializer(certificate).data
        })


# =============================================================================
# DASHBOARD & STATISTICS VIEWS
# =============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """Get overall dashboard statistics"""
    
    # Basic stats
    total_schools = School.objects.filter(is_active=True).count()
    total_users = User.objects.filter(is_active=True).count()
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status='active').count()
    
    # Donation stats
    total_donations = Donation.objects.filter(
        payment_status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Certificate stats
    total_certificates = Certificate.objects.count()
    
    # Recent activities (simplified)
    recent_activities = [
        f"New project: {project.title}" 
        for project in Project.objects.order_by('-created_at')[:5]
    ]
    
    data = {
        'total_schools': total_schools,
        'total_users': total_users,
        'total_projects': total_projects,
        'active_projects': active_projects,
        'total_donations': total_donations,
        'total_certificates': total_certificates,
        'recent_activities': recent_activities
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def impact_stats(request):
    """Get global environmental impact statistics"""
    
    impacts = EnvironmentalImpact.objects.filter(verified=True)
    
    stats = {
        'total_trees_planted': impacts.filter(impact_type='trees_planted').aggregate(Sum('value'))['value__sum'] or 0,
        'total_students_engaged': impacts.filter(impact_type='students_engaged').aggregate(Sum('value'))['value__sum'] or 0,
        'total_waste_recycled': impacts.filter(impact_type='waste_recycled').aggregate(Sum('value'))['value__sum'] or 0,
        'total_water_saved': impacts.filter(impact_type='water_saved').aggregate(Sum('value'))['value__sum'] or 0,
        'total_carbon_reduced': impacts.filter(impact_type='carbon_reduced').aggregate(Sum('value'))['value__sum'] or 0,
        'active_projects': Project.objects.filter(status='active').count(),
        'participating_schools': School.objects.filter(
            projects__status='active'
        ).distinct().count()
    }
    
    return Response(stats)


# =============================================================================
# HEALTH CHECK & ERROR HANDLERS
# =============================================================================

@require_GET
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })


def custom_404(request, exception):
    """Custom 404 handler"""
    return JsonResponse({
        'error': 'Not found',
        'message': 'The requested resource was not found',
        'status_code': 404
    }, status=404)


def custom_500(request):
    """Custom 500 handler"""
    return JsonResponse({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'status_code': 500
    }, status=500)




@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_popular_projects(request):
    from .utils import get_popular_projects
    projects = get_popular_projects(limit=10)
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_featured_projects(request):
    projects = Project.objects.filter(status='active', is_featured=True)[:10]
    serializer = ProjectSerializer(projects, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_featured_schools(request):
    from .utils import get_featured_schools
    schools = get_featured_schools(limit=10)
    serializer = SchoolSerializer(schools, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_school_members(request, pk):
    school = get_object_or_404(School, pk=pk)
    
    # Check permissions
    if not can_user_access_school(request.user, school):
        return Response({'error': 'Permission denied'}, status=403)
    
    members = school.memberships.filter(is_active=True)
    serializer = SchoolMembershipSerializer(members, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_school_projects(request, pk):
    school = get_object_or_404(School, pk=pk)
    
    # Get both led and participating projects
    led_projects = school.led_projects.filter(status='active')
    participating_projects = school.projects.filter(status='active')
    
    all_projects = led_projects.union(participating_projects)
    serializer = ProjectSerializer(all_projects, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def verify_certificate(request, verification_code):
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
    query = request.GET.get('q', '')
    projects = Project.objects.filter(
        Q(title__icontains=query) | Q(short_description__icontains=query),
        status='active'
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
    query = request.GET.get('q', '')
    schools = School.objects.filter(
        Q(name__icontains=query) | Q(city__icontains=query) | Q(country__icontains=query),
        is_active=True
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
    query = request.GET.get('q', '')
    users = User.objects.filter(
        Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query),
        is_active=True
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

from .additional_views import *