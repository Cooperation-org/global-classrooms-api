"""
URL Configuration for Global Classrooms Core API
Defines all REST API endpoints and routing
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView
)
from rest_framework_nested import routers

from . import views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'schools', views.SchoolViewSet, basename='school')
router.register(r'school-memberships', views.SchoolMembershipViewSet, basename='schoolmembership')
router.register(r'subjects', views.SubjectViewSet, basename='subject')
router.register(r'classes', views.ClassViewSet, basename='class')
router.register(r'teacher-profiles', views.TeacherProfileViewSet, basename='teacherprofile')
router.register(r'student-profiles', views.StudentProfileViewSet, basename='studentprofile')
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'project-participations', views.ProjectParticipationViewSet, basename='projectparticipation')
router.register(r'environmental-impacts', views.EnvironmentalImpactViewSet, basename='environmentalimpact')
router.register(r'donations', views.DonationViewSet, basename='donation')
router.register(r'certificates', views.CertificateViewSet, basename='certificate')

# Create nested routers for project-specific endpoints
projects_router = routers.NestedSimpleRouter(router, r'projects', lookup='project')
projects_router.register(r'goals', views.ProjectGoalViewSet, basename='project-goals')
projects_router.register(r'files', views.ProjectFileViewSet, basename='project-files')
projects_router.register(r'updates', views.ProjectUpdateViewSet, basename='project-updates')
projects_router.register(r'participants', views.ProjectParticipantViewSet, basename='project-participants')

# Define URL patterns
urlpatterns = [
    # =================================================================
    # AUTHENTICATION ENDPOINTS
    # =================================================================
    path('auth/register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='token-blacklist'),
    path('auth/wallet-register/', views.WalletRegistrationView.as_view(), name='wallet-register'),
    path('auth/login/wallet/', views.WalletLoginView.as_view(), name='wallet-login'),
    path('auth/login/google/', views.GoogleLoginView.as_view(), name='google-login'),
    path('auth/login/email/', views.EmailLoginRequestView.as_view(), name='email-login-request'),
    path('auth/login/email/verify/', views.EmailLoginVerifyView.as_view(), name='email-login-verify'),
    
    # Profile management
    path('auth/profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('auth/change-password/', views.PasswordChangeView.as_view(), name='change-password'),
    
    # =================================================================
    # DASHBOARD & STATISTICS ENDPOINTS
    # =================================================================
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('dashboard/impact-stats/', views.impact_stats, name='impact-stats'),
    
    # =================================================================
    # VIEWSET ROUTES (CRUD OPERATIONS)
    # =================================================================
    path('', include(router.urls)),
    path('', include(projects_router.urls)),
    
    # =================================================================
    # CUSTOM PROJECT ENDPOINTS
    # =================================================================
    path('projects/popular/', views.get_popular_projects, name='popular-projects'),
    path('projects/featured/', views.get_featured_projects, name='featured-projects'),
    path('projects/<uuid:pk>/join/', views.ProjectViewSet.as_view({'post': 'join'}), name='project-join'),
    path('projects/<uuid:pk>/impacts/', views.ProjectViewSet.as_view({'get': 'impacts'}), name='project-impacts'),
    path('projects/<uuid:project_id>/add-class/<uuid:class_id>/', views.add_class_to_project, name='add-class-to-project'),
    
    # =================================================================
    # CUSTOM SCHOOL ENDPOINTS
    # =================================================================
    path('schools/featured/', views.get_featured_schools, name='featured-schools'),
    path('schools/can-create/', views.can_create_school, name='can-create-school'),
    path('schools/check-exists/', views.check_school_exists, name='check-school-exists'),
    path('schools/<uuid:pk>/dashboard/', views.SchoolViewSet.as_view({'get': 'dashboard'}), name='school-dashboard'),
    path('schools/<uuid:pk>/join/', views.SchoolViewSet.as_view({'post': 'join'}), name='school-join'),
    path('schools/<uuid:pk>/members/', views.get_school_members, name='school-members'),
    path('schools/<uuid:pk>/projects/', views.get_school_projects, name='school-projects'),
    path('schools/<uuid:school_id>/add-user/', views.add_user_to_school, name='add-user-to-school'),
    path('schools/<uuid:school_id>/add-teacher-school/', views.add_teacher_to_school, name='add-teacher-to-school'),
    path('schools/<uuid:school_id>/add-student-school/', views.add_student_to_school, name='add-student-to-school'),
    path('classes/<uuid:class_id>/add-student/', views.add_student_to_class, name='add-student-to-class'),
    
    # =================================================================
    # CERTIFICATE VERIFICATION
    # =================================================================
    path('certificates/verify/<str:verification_code>/', views.verify_certificate, name='verify-certificate'),
    path('certificates/<uuid:pk>/download/', views.download_certificate, name='download-certificate'),
    
    # =================================================================
    # REPORTING ENDPOINTS
    # =================================================================
    path('reports/impact-summary/', views.impact_summary_report, name='impact-summary-report'),
    path('reports/school-activity/', views.school_activity_report, name='school-activity-report'),
    path('reports/project-progress/', views.project_progress_report, name='project-progress-report'),
    path('reports/donation-summary/', views.donation_summary_report, name='donation-summary-report'),
    
    # =================================================================
    # SEARCH ENDPOINTS
    # =================================================================
    path('search/global/', views.global_search, name='global-search'),
    path('search/projects/', views.search_projects, name='search-projects'),
    path('search/schools/', views.search_schools, name='search-schools'),
    path('search/users/', views.search_users, name='search-users'),
    
    # =================================================================
    # ADMIN ENDPOINTS
    # =================================================================
    path('admin/stats/', views.admin_dashboard_stats, name='admin-stats'),
    path('admin/verify-school/<uuid:school_id>/', views.verify_school, name='verify-school'),
    path('admin/verify-impact/<uuid:impact_id>/', views.verify_impact, name='verify-impact'),
    path('admin/featured-content/', views.manage_featured_content, name='featured-content'),
    
    # =================================================================
    # FILE UPLOAD ENDPOINTS
    # =================================================================
    path('upload/image/', views.upload_image, name='upload-image'),
    path('upload/document/', views.upload_document, name='upload-document'),
    path('upload/bulk-import/', views.bulk_import_data, name='bulk-import'),
    
    # =================================================================
    # NOTIFICATION ENDPOINTS
    # =================================================================
    path('notifications/', views.get_notifications, name='notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark-notifications-read'),
    
    # =================================================================
    # ANALYTICS ENDPOINTS
    # =================================================================
    path('analytics/project-trends/', views.project_trends, name='project-trends'),
    path('analytics/impact-trends/', views.impact_trends, name='impact-trends'),
    path('analytics/school-growth/', views.school_growth, name='school-growth'),
    path('analytics/user-engagement/', views.user_engagement, name='user-engagement'),
    
    # =================================================================
    # HEALTH CHECK
    # =================================================================
    path('health/', views.health_check, name='health-check'),
]