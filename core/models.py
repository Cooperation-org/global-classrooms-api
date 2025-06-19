from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from django.core.mail import send_mail
import random

class User(AbstractUser):
    """Extended User model for Global Classrooms"""
    USER_ROLES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('school_admin', 'School Admin'),
        ('super_admin', 'Super Admin'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=USER_ROLES, default='student')
    mobile_number = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    is_active_user = models.BooleanField(default=True)
    date_joined_school = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Wallet/account fields
    wallet_address = models.CharField(max_length=255, blank=True, null=True)
    google_account_id = models.CharField(max_length=255, blank=True, null=True)
    signup_method = models.CharField(
        max_length=50,
        choices=[
            ('wallet', 'Wallet'),
            ('custodial', 'Custodial Wallet'),
            ('google', 'Google'),
        ],
        default='wallet'
    )

       # Fix the reverse accessor conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='core_users',  # Changed from default 'user_set'
        related_query_name='core_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='core_users',  # Changed from default 'user_set'
        related_query_name='core_user',
    )


    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


class EmailLoginOTP(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > 600  # 10 minutes


class School(models.Model):
    """School model based on Figma school details form"""
    INSTITUTION_TYPES = [
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('high_school', 'High School'),
        ('university', 'University'),
        ('college', 'College'),
        ('academy', 'Academy'),
        ('other', 'Other'),
    ]
    
    AFFILIATION_TYPES = [
        ('government', 'Government'),
        ('private', 'Private'),
        ('semi_private', 'Semi-Private'),
        ('ngo', 'NGO'),
        ('international', 'International'),
    ]
    
    MEDIUM_OF_INSTRUCTION = [
        ('english', 'English'),
        ('local_language', 'Local Language'),
        ('bilingual', 'Bilingual'),
        ('multilingual', 'Multilingual'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    overview = models.TextField(blank=True, null=True)
    institution_type = models.CharField(max_length=50, choices=INSTITUTION_TYPES)
    affiliation = models.CharField(max_length=50, choices=AFFILIATION_TYPES)
    registration_number = models.CharField(max_length=100, unique=True)
    year_of_establishment = models.IntegerField(
        validators=[MinValueValidator(1800), MaxValueValidator(timezone.now().year)]
    )
    
    # Address Information
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    # Contact Information
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    
    # Principal/Head Information
    principal_name = models.CharField(max_length=255)
    principal_email = models.EmailField()
    principal_phone = models.CharField(max_length=20)
    
    # School Statistics
    number_of_students = models.PositiveIntegerField(default=0)
    number_of_teachers = models.PositiveIntegerField(default=0)
    medium_of_instruction = models.CharField(max_length=50, choices=MEDIUM_OF_INSTRUCTION)
    
    # School Logo
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    
    # Meta Information
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Admin who manages this school
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_schools')

    def __str__(self):
        return self.name


class SchoolMembership(models.Model):
    """Links users to schools with specific roles"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='school_memberships')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='memberships')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'school']

    def __str__(self):
        return f"{self.user.username} at {self.school.name}"


class Subject(models.Model):
    """Subjects that can be taught/studied"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name


class Class(models.Model):
    """Class/Grade levels"""
    name = models.CharField(max_length=50)  # e.g., "Grade 5", "Class 10", "Form 1"
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classes')
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.school.name}"


class TeacherProfile(models.Model):
    """Extended profile for teachers"""
    TEACHER_ROLES = [
        ('class_teacher', 'Class Teacher'),
        ('subject_teacher', 'Subject Teacher'),
        ('admin', 'Admin'),
        ('coordinator', 'Coordinator'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teachers')
    teacher_role = models.CharField(max_length=20, choices=TEACHER_ROLES, default='subject_teacher')
    assigned_subjects = models.ManyToManyField(Subject, blank=True, related_name='teachers')
    assigned_classes = models.ManyToManyField(Class, blank=True, related_name='teachers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    join_link = models.UUIDField(default=uuid.uuid4, unique=True)  # For teacher invitation
    
    def __str__(self):
        return f"Teacher: {self.user.get_full_name()} at {self.school.name}"


class StudentProfile(models.Model):
    """Extended profile for students"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    student_id = models.CharField(max_length=50)  # School's internal student ID
    current_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    parent_name = models.CharField(max_length=255, blank=True, null=True)
    parent_email = models.EmailField(blank=True, null=True)
    parent_phone = models.CharField(max_length=20, blank=True, null=True)
    enrollment_date = models.DateField(default=timezone.now)
    
    def __str__(self):
        return f"Student: {self.user.get_full_name()} ({self.student_id})"


class Project(models.Model):
    """Environmental projects that schools can participate in"""
    ENVIRONMENTAL_THEMES = [
        ('water_conservation', 'Water Conservation'),
        ('waste_management', 'Waste Management'),
        ('renewable_energy', 'Renewable Energy'),
        ('biodiversity', 'Biodiversity'),
        ('climate_change', 'Climate Change'),
        ('sustainable_agriculture', 'Sustainable Agriculture'),
        ('air_quality', 'Air Quality'),
        ('ocean_conservation', 'Ocean Conservation'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    short_description = models.CharField(max_length=250)
    detailed_description = models.TextField()
    cover_image = models.ImageField(upload_to='project_covers/', blank=True, null=True)
    
    # Project Scope
    environmental_themes = models.JSONField(default=list)  # Multiple themes can be selected
    
    # Timeline
    start_date = models.DateField()
    end_date = models.DateField()
    is_open_for_collaboration = models.BooleanField(default=True)
    
    # Goals and Rewards
    goals = models.JSONField(default=list)  # List of project goals
    offer_rewards = models.BooleanField(default=False)
    recognition_type = models.CharField(max_length=100, blank=True, null=True)
    award_criteria = models.TextField(blank=True, null=True)
    
    # Certificates and Badges
    certificate_template = models.FileField(upload_to='certificates/', blank=True, null=True)
    badge_image = models.ImageField(upload_to='badges/', blank=True, null=True)
    
    # School Information
    lead_school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='led_projects')
    participating_schools = models.ManyToManyField(School, through='ProjectParticipation', related_name='projects')
    
    # Contact Information
    contact_person_name = models.CharField(max_length=255)
    contact_person_email = models.EmailField()
    contact_person_role = models.CharField(max_length=100)
    contact_country = models.CharField(max_length=100)
    contact_city = models.CharField(max_length=100)
    
    # Media and Attachments
    supporting_files = models.JSONField(default=list)  # File paths for supporting documents
    media_files = models.JSONField(default=list)  # Image and video paths
    
    # Project Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.lead_school.name}"


class ProjectParticipation(models.Model):
    """Tracks school participation in projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    contribution_description = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['project', 'school']

    def __str__(self):
        return f"{self.school.name} in {self.project.title}"


class EnvironmentalImpact(models.Model):
    """Tracks environmental impact metrics"""
    IMPACT_TYPES = [
        ('trees_planted', 'Trees Planted'),
        ('waste_recycled', 'Waste Recycled (kg)'),
        ('water_saved', 'Water Saved (liters)'),
        ('energy_saved', 'Energy Saved (kWh)'),
        ('carbon_reduced', 'Carbon Reduced (kg CO2)'),
        ('students_engaged', 'Students Engaged'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='impacts')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='impacts')
    impact_type = models.CharField(max_length=50, choices=IMPACT_TYPES)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50)
    measurement_date = models.DateField(default=timezone.now)
    verified = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.impact_type}: {self.value} {self.unit} - {self.school.name}"


class Donation(models.Model):
    """Donation tracking for GoodCollective integration"""
    PAYMENT_METHODS = [
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('goodcollective', 'GoodCollective Wallet'),
    ]
    
    DONATION_PURPOSES = [
        ('general', 'General Support'),
        ('trees', 'Tree Planting'),
        ('water_conservation', 'Water Conservation'),
        ('education', 'Educational Materials'),
        ('technology', 'Technology Access'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor_name = models.CharField(max_length=255)
    donor_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    purpose = models.CharField(max_length=50, choices=DONATION_PURPOSES, default='general')
    recipient_name = models.CharField(max_length=255, blank=True, null=True)  # Honor/memory donations
    send_ecard = models.BooleanField(default=False)
    recipient_email = models.EmailField(blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    
    # Payment Processing
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    payment_status = models.CharField(max_length=50, default='pending')
    processed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"${self.amount} from {self.donor_name}"


class Certificate(models.Model):
    """Certificates awarded to users"""
    CERTIFICATE_TYPES = [
        ('project_completion', 'Project Completion'),
        ('environmental_impact', 'Environmental Impact'),
        ('collaboration', 'Cross-School Collaboration'),
        ('leadership', 'Environmental Leadership'),
        ('honor', 'Certificate of Honor'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    certificate_type = models.CharField(max_length=50, choices=CERTIFICATE_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Certificate Design
    template_file = models.FileField(upload_to='certificate_templates/')
    background_color = models.CharField(max_length=7, default='#4ADE80')  # Green theme from Figma
    
    # Verification
    verification_code = models.UUIDField(default=uuid.uuid4, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='issued_certificates')

    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"