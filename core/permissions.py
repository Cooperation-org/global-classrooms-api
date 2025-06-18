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