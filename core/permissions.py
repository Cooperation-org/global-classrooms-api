"""
Custom permissions for Global Classrooms API
Implements role-based access control
"""

from rest_framework import permissions
from django.db.models import Q


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsSchoolAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission for school-related objects.
    Only school admins can modify their school data.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions only for school admin or staff
        if request.user.is_staff:
            return True
            
        if hasattr(obj, 'admin'):
            return obj.admin == request.user
        elif hasattr(obj, 'school'):
            return obj.school.admin == request.user
        
        return False


class IsTeacherOrReadOnly(permissions.BasePermission):
    """
    Custom permission for teacher-related operations.
    Teachers can modify data related to their schools.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions for staff, school admins, or teachers
        if request.user.is_staff:
            return True
        
        # Check if user is a teacher or school admin
        user_roles = ['teacher', 'school_admin']
        return request.user.role in user_roles
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # School admin can modify anything in their school
        if hasattr(obj, 'school') and obj.school.admin == request.user:
            return True
        
        # Teachers can modify their own data
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Teachers can modify data from their schools
        if hasattr(obj, 'school'):
            user_schools = request.user.school_memberships.filter(
                is_active=True
            ).values_list('school', flat=True)
            return obj.school.id in user_schools
        
        return False


class IsStudentOrTeacherForSchool(permissions.BasePermission):
    """
    Permission for student-related operations.
    Students can view/edit their own data, teachers can view/edit students in their schools.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Students can access their own data
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # School admin can access students in their school
        if hasattr(obj, 'school') and obj.school.admin == request.user:
            return True
        
        # Teachers can access students in their schools
        if request.user.role in ['teacher', 'school_admin']:
            if hasattr(obj, 'school'):
                user_schools = request.user.school_memberships.filter(
                    is_active=True
                ).values_list('school', flat=True)
                return obj.school.id in user_schools
        
        return False


class IsProjectCreatorOrCollaborator(permissions.BasePermission):
    """
    Permission for project-related operations.
    Project creators and collaborating schools can modify project data.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Project creator can modify
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        # Lead school admin can modify
        if hasattr(obj, 'lead_school') and obj.lead_school.admin == request.user:
            return True
        
        # Collaborating school admins can modify
        if hasattr(obj, 'participating_schools'):
            user_schools = request.user.managed_schools.all()
            collaborating_schools = obj.participating_schools.all()
            return any(school in collaborating_schools for school in user_schools)
        
        return False


class IsProjectOwnerOrParticipant(permissions.BasePermission):
    """
    Custom permission to only allow project owners or active participants to edit a project.
    Read-only for other authenticated users.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner or a participant.
        # 1. Check if the user is the project creator
        if obj.created_by == request.user:
            return True
            
        # 2. Check if the user is a member of the lead school
        if obj.lead_school.memberships.filter(user=request.user, is_active=True).exists():
            return True

        # 3. Check if the user is a member of any participating school
        user_school_ids = request.user.school_memberships.filter(is_active=True).values_list('school_id', flat=True)
        project_school_ids = obj.participating_schools.all().values_list('id', flat=True)
        
        # Check for intersection between the user's schools and the project's schools
        if set(user_school_ids).intersection(set(project_school_ids)):
            return True

        return False


class IsCertificateRecipientOrIssuer(permissions.BasePermission):
    """
    Permission for certificate operations.
    Recipients can view their certificates, issuers can manage certificates they created.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Recipients can view their certificates
        if hasattr(obj, 'recipient') and obj.recipient == request.user:
            return request.method in permissions.SAFE_METHODS
        
        # Certificate issuers can manage certificates they created
        if hasattr(obj, 'issued_by') and obj.issued_by == request.user:
            return True
        
        return False


class IsDonorOrStaff(permissions.BasePermission):
    """
    Permission for donation operations.
    Anyone can create donations, only staff can view all donations.
    """
    
    def has_permission(self, request, view):
        # Anyone can create donations
        if request.method == 'POST':
            return True
        
        # Only authenticated users can view donations
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # For transparency, completed donations are publicly viewable
        if request.method in permissions.SAFE_METHODS:
            return obj.payment_status == 'completed'
        
        return False


class IsSchoolMember(permissions.BasePermission):
    """
    Permission to check if user is a member of a specific school.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_school_membership(self, user, school):
        """Check if user is a member of the school"""
        return user.school_memberships.filter(
            school=school, 
            is_active=True
        ).exists()


class CanViewSchoolData(permissions.BasePermission):
    """
    Permission for viewing school-specific data.
    School members can view data from their schools.
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Staff can view everything
        if request.user.is_staff:
            return True
        
        # Get the school from the object
        school = None
        if hasattr(obj, 'school'):
            school = obj.school
        elif hasattr(obj, 'lead_school'):
            school = obj.lead_school
        elif hasattr(obj, 'admin'):  # For School model itself
            school = obj
        
        if school:
            # School admin can view everything
            if school.admin == request.user:
                return True
            
            # School members can view school data
            return request.user.school_memberships.filter(
                school=school,
                is_active=True
            ).exists()
        
        return False


# Utility functions for role checking
def is_school_admin(user, school):
    """Check if user is admin of the school"""
    return school.admin == user or user.is_staff


def is_school_member(user, school):
    """Check if user is a member of the school"""
    return user.school_memberships.filter(
        school=school,
        is_active=True
    ).exists()


def get_user_schools(user):
    """Get all schools where user is a member"""
    return user.school_memberships.filter(
        is_active=True
    ).values_list('school', flat=True)


def can_user_access_school(user, school):
    """Check if user can access school data"""
    if user.is_staff:
        return True
    
    # School admin
    if school.admin == user:
        return True
    
    # School member
    return is_school_member(user, school)


def can_user_modify_school(user, school):
    """Check if user can modify school data"""
    if user.is_staff:
        return True
    
    # Only school admin can modify
    return school.admin == user


class CanCreateSchool(permissions.BasePermission):
    """
    Permission to control who can create schools.
    Only teachers and school admins can create schools.
    """
    
    def has_permission(self, request, view):
        # Only authenticated users can create schools
        if not request.user.is_authenticated:
            return False
        
        # Staff can always create schools
        if request.user.is_staff:
            return True
        
        # Super admins can create schools
        if request.user.role == 'super_admin':
            return True
        
        # Check if user has the right role
        if request.user.role in ['school_admin', 'teacher']:
            return True
        
        return False


class CanCreateProject(permissions.BasePermission):
    """
    Permission to control who can create projects.
    Only school members (teachers, school_admins) can create projects.
    """
    
    def has_permission(self, request, view):
        # Only authenticated users can create projects
        if not request.user.is_authenticated:
            return False
        
        # Staff can always create projects
        if request.user.is_staff:
            return True
        
        # Super admins can create projects
        if request.user.role == 'super_admin':
            return True
        
        # School admins can create projects
        if request.user.role == 'school_admin':
            return True
        
        # Teachers can create projects
        if request.user.role == 'teacher':
            return True
        
        # Students and donors cannot create projects
        return False


class CanManageSchoolContent(permissions.BasePermission):
    """
    Permission for managing school-related content (students, teachers, classes).
    Only school admins and teachers from the same school can manage content.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Only school admins and teachers can manage school content
        return request.user.role in ['school_admin', 'teacher']
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Get the school from the object
        school = None
        if hasattr(obj, 'school'):
            school = obj.school
        elif hasattr(obj, 'admin'):  # For School model itself
            school = obj
        
        if not school:
            return False
        
        # School admin can manage everything in their school
        if school.admin == request.user:
            return True
        
        # Teachers can manage content in schools they're members of
        if request.user.role == 'teacher':
            return request.user.school_memberships.filter(
                school=school,
                is_active=True
            ).exists()
        
        return False


class CanJoinProject(permissions.BasePermission):
    """
    Permission to control who can join projects.
    Only school members can join projects on behalf of their schools.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Users must be members of at least one school to join projects
        return request.user.school_memberships.filter(is_active=True).exists()


class CanManageProjectContent(permissions.BasePermission):
    """
    Permission for managing project-related content (goals, files, updates).
    Only project creators and participating school members can manage content.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Users must be school members to contribute to projects
        return request.user.school_memberships.filter(is_active=True).exists()
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Get the project from the object
        project = None
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'created_by'):  # For Project model itself
            project = obj
        
        if not project:
            return False
        
        # Project creator can manage
        if project.created_by == request.user:
            return True
        
        # Lead school members can manage
        if request.user.school_memberships.filter(
            school=project.lead_school,
            is_active=True
        ).exists():
            return True
        
        # Participating school members can manage
        user_schools = request.user.school_memberships.filter(
            is_active=True
        ).values_list('school', flat=True)
        
        project_schools = project.participating_schools.values_list('id', flat=True)
        
        return bool(set(user_schools).intersection(set(project_schools)))


class CanUpdateProjectProgress(permissions.BasePermission):
    """
    Permission for updating project progress (ProjectUpdate model).
    Students, teachers, and school admins can add progress updates if they're part of the project.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Users must be school members to contribute to projects
        return request.user.school_memberships.filter(is_active=True).exists()
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Get the project from the object
        project = None
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'created_by'):  # For Project model itself
            project = obj
        
        if not project:
            return False
        
        # Project creator can manage
        if project.created_by == request.user:
            return True
        
        # Lead school members (including students) can add progress updates
        if request.user.school_memberships.filter(
            school=project.lead_school,
            is_active=True
        ).exists():
            return True
        
        # Participating school members (including students) can add progress updates
        user_schools = request.user.school_memberships.filter(
            is_active=True
        ).values_list('school', flat=True)
        
        project_schools = project.participating_schools.values_list('id', flat=True)
        
        return bool(set(user_schools).intersection(set(project_schools)))


class CanManageProjectStructure(permissions.BasePermission):
    """
    Permission for managing project structure (goals, files, main project details).
    Only teachers, school admins, and super admins can modify project structure.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Only teachers and school admins can manage project structure
        return request.user.role in ['teacher', 'school_admin', 'super_admin']
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Get the project from the object
        project = None
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'created_by'):  # For Project model itself
            project = obj
        
        if not project:
            return False
        
        # Project creator can manage
        if project.created_by == request.user:
            return True
        
        # Only teachers and school admins from participating schools can manage structure
        if request.user.role not in ['teacher', 'school_admin', 'super_admin']:
            return False
        
        # Lead school teachers/admins can manage
        if (request.user.school_memberships.filter(
            school=project.lead_school,
            is_active=True
        ).exists() and request.user.role in ['teacher', 'school_admin']):
            return True
        
        # Participating school teachers/admins can manage
        user_schools = request.user.school_memberships.filter(
            is_active=True
        ).values_list('school', flat=True)
        
        project_schools = project.participating_schools.values_list('id', flat=True)
        
        return (bool(set(user_schools).intersection(set(project_schools))) and 
                request.user.role in ['teacher', 'school_admin'])


class CanManageSchoolMembers(permissions.BasePermission):
    """
    Permission for school admins to add/remove teachers and students to/from their school.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Only school admins can manage school members
        return request.user.role in ['school_admin', 'super_admin']
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Get the school from the object
        school = None
        if hasattr(obj, 'school'):
            school = obj.school
        elif hasattr(obj, 'admin'):  # For School model itself
            school = obj
        
        if not school:
            return False
        
        # Only the school admin can manage members of their school
        return school.admin == request.user


class CanManageProjectParticipants(permissions.BasePermission):
    """
    Permission for teachers to add/remove students to/from projects.
    Only teachers from the lead school or participating schools can manage participants.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Only teachers and school admins can manage project participants
        return request.user.role in ['teacher', 'school_admin', 'super_admin']
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Get the project from the object
        project = None
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'created_by'):  # For Project model itself
            project = obj
        
        if not project:
            return False
        
        # Project creator can manage participants
        if project.created_by == request.user:
            return True
        
        # Only teachers/admins from lead school can manage participants
        if (request.user.school_memberships.filter(
            school=project.lead_school,
            is_active=True
        ).exists() and request.user.role in ['teacher', 'school_admin']):
            return True
        
        # Teachers/admins from participating schools can manage their own school's participants
        user_schools = request.user.school_memberships.filter(
            is_active=True
        ).values_list('school', flat=True)
        
        project_schools = project.participating_schools.values_list('id', flat=True)
        
        return (bool(set(user_schools).intersection(set(project_schools))) and 
                request.user.role in ['teacher', 'school_admin'])


class CanUploadProjectProgress(permissions.BasePermission):
    """
    Permission for students to upload progress to projects they're participants in.
    Only students who are explicitly added to projects can upload progress.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # All school members can potentially upload progress
        return request.user.school_memberships.filter(is_active=True).exists()
    
    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user.is_staff:
            return True
        
        # Get the project from the object
        project = None
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'created_by'):  # For Project model itself
            project = obj
        
        if not project:
            return False
        
        # Teachers and school admins can always upload
        if request.user.role in ['teacher', 'school_admin', 'super_admin']:
            # Check if they're from participating schools
            user_schools = request.user.school_memberships.filter(
                is_active=True
            ).values_list('school', flat=True)
            
            project_schools = list(project.participating_schools.values_list('id', flat=True))
            if project.lead_school.id not in project_schools:
                project_schools.append(project.lead_school.id)
            
            return bool(set(user_schools).intersection(set(project_schools)))
        
        # Students can only upload if they're explicitly added as project participants
        if request.user.role == 'student':
            from .models import ProjectParticipant
            return ProjectParticipant.objects.filter(
                project=project,
                student=request.user,
                is_active=True
            ).exists()
        
        return False