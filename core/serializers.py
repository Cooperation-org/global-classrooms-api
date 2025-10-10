"""
Serializers for Global Classrooms API
Converts Django models to/from JSON for REST API endpoints
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import (
    User, School, Subject, Class, TeacherProfile, StudentProfile,
    Project, ProjectParticipation, EnvironmentalImpact, Donation,
    Certificate, SchoolMembership, ProjectGoal, ProjectFile, ProjectUpdate, ProjectUpdateMedia,
    ProjectParticipant
)


# =============================================================================
# USER SERIALIZERS
# =============================================================================

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)
    wallet_address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    google_account_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    signup_method = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 'first_name', 
            'last_name', 'role', 'mobile_number', 'gender', 'date_of_birth',
            'city', 'country', 'wallet_address', 'google_account_id', 'signup_method'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def validate_email(self, value):
        """Check if email is already registered"""
        from .models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email address already exists. Please sign in instead.")
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        validated_data['username'] = validated_data['email']
        validated_data['signup_method'] = 'email'
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    full_name = serializers.SerializerMethodField()
    school_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'mobile_number', 'gender', 'date_of_birth', 'profile_picture',
            'city', 'country', 'is_active', 'date_joined', 'school_count', 'signup_method'
        ]
        read_only_fields = ['id', 'date_joined', 'full_name', 'school_count']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_school_count(self, obj):
        return obj.school_memberships.filter(is_active=True).count()


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'mobile_number', 'gender', 
            'date_of_birth', 'profile_picture', 'city', 'country',
            'role'
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


# =============================================================================
# SCHOOL SERIALIZERS
# =============================================================================

class SchoolSerializer(serializers.ModelSerializer):
    """Serializer for school details"""
    admin_name = serializers.CharField(source='admin.get_full_name', read_only=True)
    member_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    
    class Meta:
        model = School
        fields = [
            'id', 'name', 'overview', 'institution_type', 'affiliation',
            'registration_number', 'year_of_establishment', 'address_line_1',
            'address_line_2', 'city', 'state', 'postal_code', 'country',
            'phone_number', 'email', 'website', 'principal_name',
            'principal_email', 'principal_phone', 'number_of_students',
            'number_of_teachers', 'medium_of_instruction', 'logo',
            'is_verified', 'is_active', 'created_at', 'admin', 'admin_name',
            'member_count', 'project_count'
        ]
        read_only_fields = ['id', 'created_at', 'admin_name', 'member_count', 'project_count']
    
    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()
    
    def get_project_count(self, obj):
        return obj.led_projects.filter(status='active').count() + obj.projects.filter(status='active').count()


class SchoolCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating schools"""

    creator_name = serializers.CharField(write_only=True)
    creator_role = serializers.ChoiceField(choices=[choice for choice in User.USER_ROLES if choice[0] in ('student', 'teacher')], write_only=True)
    
    class Meta:
        model = School
        fields = [
            'name', 'overview', 'institution_type', 'affiliation',
            'registration_number', 'year_of_establishment', 'address_line_1',
            'address_line_2', 'city', 'state', 'postal_code', 'country',
            'phone_number', 'email', 'website', 'principal_name',
            'principal_email', 'principal_phone', 'number_of_students',
            'number_of_teachers', 'medium_of_instruction', 'logo',
            'creator_name', 'creator_role'
        ]
    
    def validate(self, attrs):
        """Validate school creation data"""
        
        # Check if school with same name exists in same city/country
        existing_school = School.objects.filter(
            name__iexact=attrs['name'],
            city__iexact=attrs['city'],
            country__iexact=attrs['country'],
            is_active=True
        ).exists()
        
        if existing_school:
            raise serializers.ValidationError(
                f"A school named '{attrs['name']}' already exists in {attrs['city']}, {attrs['country']}. "
                "Please choose a different name or verify this is not a duplicate."
            )
        
        # Check if registration number is unique
        if attrs.get('registration_number'):
            existing_reg = School.objects.filter(
                registration_number=attrs['registration_number'],
                is_active=True
            ).exists()
            
            if existing_reg:
                raise serializers.ValidationError(
                    f"A school with registration number '{attrs['registration_number']}' already exists."
                )
        
        return attrs
    
    def create(self, validated_data):

        creator_name = validated_data.pop('creator_name')
        creator_role = validated_data.pop('creator_role')

        user = self.context['request'].user
        
        name_parts = creator_name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'role': creator_role,
        }
        user_serializer = UserUpdateSerializer(user, data=user_data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()

        # Set the admin to the current user (creator becomes admin)
        validated_data['admin'] = user

        school = super().create(validated_data)
        
        # Automatically create a school membership for the creator
        SchoolMembership.objects.create(
            user=self.context['request'].user,
            school=school,
            is_active=True
        )
        
        return school


class SchoolMembershipSerializer(serializers.ModelSerializer):
    """Serializer for school memberships"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = SchoolMembership
        fields = ['id', 'user', 'school', 'user_name', 'user_role', 'school_name', 'joined_at', 'is_active']
        read_only_fields = ['id', 'joined_at']


# =============================================================================
# SUBJECT & CLASS SERIALIZERS
# =============================================================================

class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for subjects"""
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'description', 'is_active']


class ClassSerializer(serializers.ModelSerializer):
    """Serializer for classes"""
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = Class
        fields = ['id', 'name', 'school', 'school_name', 'description']


# =============================================================================
# PROFILE SERIALIZERS
# =============================================================================

class TeacherProfileSerializer(serializers.ModelSerializer):
    """Serializer for teacher profiles"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    assigned_subjects_data = SubjectSerializer(source='assigned_subjects', many=True, read_only=True)
    assigned_classes_data = ClassSerializer(source='assigned_classes', many=True, read_only=True)
    
    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user', 'school', 'user_name', 'school_name', 'teacher_role',
            'assigned_subjects', 'assigned_classes', 'assigned_subjects_data',
            'assigned_classes_data', 'status', 'join_link'
        ]
        read_only_fields = ['id', 'join_link']


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for student profiles"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    class_name = serializers.CharField(source='current_class.name', read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'school', 'user_name', 'school_name', 'student_id',
            'current_class', 'class_name', 'parent_name', 'parent_email',
            'parent_phone', 'enrollment_date'
        ]
        read_only_fields = ['id']


# =============================================================================
# PROJECT SERIALIZERS
# =============================================================================

class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for project details"""
    lead_school_name = serializers.CharField(source='lead_school.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    participating_schools_count = serializers.SerializerMethodField()
    total_impact = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'short_description', 'detailed_description',
            'cover_image', 'environmental_themes', 'start_date', 'end_date',
            'is_open_for_collaboration', 'offer_rewards',
            'recognition_type', 'award_criteria', 'lead_school',
            'lead_school_name', 'contact_person_name', 'contact_person_email',
            'contact_person_role', 'contact_country', 'contact_city',
            'media_files', 'status', 'created_by',
            'created_by_name', 'created_at', 'updated_at',
            'participating_schools_count', 'total_impact'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_participating_schools_count(self, obj):
        return obj.participating_schools.filter(projectparticipation__is_active=True).count()
    
    def get_total_impact(self, obj):
        impacts = obj.impacts.filter(verified=True)
        return {
            'trees_planted': sum(impact.value for impact in impacts.filter(impact_type='trees_planted')),
            'students_engaged': sum(impact.value for impact in impacts.filter(impact_type='students_engaged')),
            'waste_recycled': sum(impact.value for impact in impacts.filter(impact_type='waste_recycled')),
        }


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating projects"""
    goals = serializers.ListField(
        child=serializers.CharField(max_length=255),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Project
        fields = [
            'title', 'short_description', 'detailed_description', 'cover_image',
            'environmental_themes', 'start_date', 'end_date', 'is_open_for_collaboration',
            'offer_rewards', 'recognition_type', 'award_criteria',
            'lead_school', 'contact_person_name', 'contact_person_email',
            'contact_person_role', 'contact_country', 'contact_city', 'goals'
        ]
    
    def create(self, validated_data):
        goals_data = validated_data.pop('goals', [])
        validated_data['created_by'] = self.context['request'].user
        project = super().create(validated_data)
        for goal_description in goals_data:
            ProjectGoal.objects.create(project=project, description=goal_description)
        return project


class ProjectGoalSerializer(serializers.ModelSerializer):
    """Serializer for project goals"""
    class Meta:
        model = ProjectGoal
        fields = ['id', 'project', 'description', 'is_completed', 'completed_at']
        read_only_fields = ['id', 'project', 'completed_at']


class ProjectFileSerializer(serializers.ModelSerializer):
    """Serializer for project files"""
    class Meta:
        model = ProjectFile
        fields = ['id', 'project', 'file', 'description', 'uploaded_at']
        read_only_fields = ['id', 'project', 'uploaded_at']


class ProjectUpdateMediaSerializer(serializers.ModelSerializer):
    """Serializer for media files attached to a project update."""
    class Meta:
        model = ProjectUpdateMedia
        fields = ['id', 'file', 'media_type']


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and viewing project updates."""
    media = ProjectUpdateMediaSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(
        child=serializers.FileField(), write_only=True
    )
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = ProjectUpdate
        fields = [
            'id', 'project', 'school', 'school_name', 'uploaded_by', 'uploaded_by_name',
            'description', 'created_at', 'media', 'uploaded_files'
        ]
        read_only_fields = ['id', 'project', 'school', 'school_name', 'uploaded_by', 'uploaded_by_name', 'created_at']

    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files')
        update = ProjectUpdate.objects.create(**validated_data)

        for file in uploaded_files:
            # Simple content-type based check
            media_type = 'file'
            if file.content_type.startswith('image'):
                media_type = 'image'
            elif file.content_type.startswith('video'):
                media_type = 'video'
            
            ProjectUpdateMedia.objects.create(update=update, file=file, media_type=media_type)

        return update


class ProjectParticipationSerializer(serializers.ModelSerializer):
    """Serializer for project participation"""
    project_title = serializers.CharField(source='project.title', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = ProjectParticipation
        fields = [
            'id', 'project', 'school', 'project_title', 'school_name',
            'joined_at', 'is_active', 'contribution_description'
        ]
        read_only_fields = ['id', 'joined_at']


# =============================================================================
# ENVIRONMENTAL IMPACT SERIALIZERS
# =============================================================================

class EnvironmentalImpactSerializer(serializers.ModelSerializer):
    """Serializer for environmental impacts"""
    project_title = serializers.CharField(source='project.title', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = EnvironmentalImpact
        fields = [
            'id', 'project', 'school', 'project_title', 'school_name',
            'impact_type', 'value', 'unit', 'measurement_date',
            'verified', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ImpactStatsSerializer(serializers.Serializer):
    """Serializer for impact statistics"""
    total_trees_planted = serializers.IntegerField()
    total_students_engaged = serializers.IntegerField()
    total_waste_recycled = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_water_saved = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_carbon_reduced = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_projects = serializers.IntegerField()
    participating_schools = serializers.IntegerField()


# =============================================================================
# DONATION SERIALIZERS
# =============================================================================

class DonationSerializer(serializers.ModelSerializer):
    """Serializer for donations"""
    
    class Meta:
        model = Donation
        fields = [
            'id', 'donor_name', 'donor_email', 'amount', 'payment_method',
            'purpose', 'recipient_name', 'send_ecard', 'recipient_email',
            'message', 'payment_status', 'created_at'
        ]
        read_only_fields = ['id', 'payment_status', 'created_at']


class DonationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating donations"""
    
    class Meta:
        model = Donation
        fields = [
            'donor_name', 'donor_email', 'amount', 'payment_method',
            'purpose', 'recipient_name', 'send_ecard', 'recipient_email', 'message'
        ]


# =============================================================================
# CERTIFICATE SERIALIZERS
# =============================================================================

class CertificateSerializer(serializers.ModelSerializer):
    """Serializer for certificates"""
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.get_full_name', read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'recipient', 'recipient_name', 'certificate_type', 'title',
            'description', 'project', 'project_title', 'template_file',
            'background_color', 'verification_code', 'issued_at',
            'issued_by', 'issued_by_name'
        ]
        read_only_fields = ['id', 'verification_code', 'issued_at']


# =============================================================================
# DASHBOARD SERIALIZERS
# =============================================================================

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_schools = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_projects = serializers.IntegerField()
    active_projects = serializers.IntegerField()
    total_donations = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_certificates = serializers.IntegerField()
    recent_activities = serializers.ListField()


class SchoolDashboardSerializer(serializers.Serializer):
    """Serializer for school-specific dashboard"""
    school_info = SchoolSerializer()
    member_count = serializers.IntegerField()
    project_count = serializers.IntegerField()
    total_impact = ImpactStatsSerializer()
    recent_projects = ProjectSerializer(many=True)
    recent_impacts = EnvironmentalImpactSerializer(many=True)


# =============================================================================
# PROJECT PARTICIPANT SERIALIZERS
# =============================================================================

class ProjectParticipantSerializer(serializers.ModelSerializer):
    """Serializer for project participants"""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    class_name = serializers.CharField(source='student_class.name', read_only=True)
    added_by_name = serializers.CharField(source='added_by.get_full_name', read_only=True)
    
    class Meta:
        model = ProjectParticipant
        fields = [
            'id', 'project', 'student', 'student_name', 'student_email',
            'student_class', 'class_name', 'added_by', 'added_by_name',
            'joined_at', 'is_active'
        ]
        read_only_fields = ['id', 'joined_at', 'added_by']