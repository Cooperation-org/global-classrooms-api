# core/management/commands/load_sample_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import (
    School, Subject, Class, TeacherProfile, StudentProfile, 
    Project, EnvironmentalImpact, Donation, Certificate
)
from datetime import date, timedelta
import uuid

User = get_user_model()

class Command(BaseCommand):
    help = 'Load sample data for Global Classrooms'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading sample data...'))
        
        # Create sample subjects
        subjects = [
            'Mathematics', 'Science', 'English', 'History', 'Geography',
            'Environmental Studies', 'Art', 'Physical Education', 'Computer Science'
        ]
        for subject_name in subjects:
            Subject.objects.get_or_create(name=subject_name)
        
        # Create sample school admin
        admin_user, created = User.objects.get_or_create(
            username='school_admin',
            defaults={
                'email': 'admin@greenwood.edu',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'role': 'school_admin',
                'mobile_number': '+1-555-0123',
                'gender': 'female',
                'city': 'San Francisco',
                'country': 'United States'
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        
        # Create sample school
        school, created = School.objects.get_or_create(
            name='Greenwood Elementary Academy',
            defaults={
                'overview': 'A progressive elementary school focused on environmental education and sustainability.',
                'institution_type': 'primary',
                'affiliation': 'private',
                'registration_number': 'GEA-2020-001',
                'year_of_establishment': 2020,
                'address_line_1': '123 Oak Street',
                'city': 'San Francisco',
                'state': 'California',
                'postal_code': '94102',
                'country': 'United States',
                'phone_number': '+1-555-0123',
                'email': 'info@greenwood.edu',
                'website': 'https://greenwood.edu',
                'principal_name': 'Dr. Michael Anderson',
                'principal_email': 'principal@greenwood.edu',
                'principal_phone': '+1-555-0124',
                'number_of_students': 450,
                'number_of_teachers': 25,
                'medium_of_instruction': 'english',
                'admin': admin_user
            }
        )
        
        # Create sample classes
        classes = ['Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5']
        for class_name in classes:
            Class.objects.get_or_create(
                name=class_name,
                school=school,
                defaults={'description': f'{class_name} curriculum focused on environmental awareness'}
            )
        
        # Create sample teachers
        teachers_data = [
            {
                'username': 'evelyn_carter',
                'email': 'evelyn.carter@example.com',
                'first_name': 'Ms. Evelyn',
                'last_name': 'Carter',
                'subjects': ['Mathematics'],
                'role_type': 'class_teacher'
            },
            {
                'username': 'charles_bennett',
                'email': 'charles.bennett@example.com',
                'first_name': 'Mr. Charles',
                'last_name': 'Bennett',
                'subjects': ['Science'],
                'role_type': 'subject_teacher'
            },
            {
                'username': 'sophia_carter',
                'email': 'sophia.carter@example.com',
                'first_name': 'Ms. Sophia',
                'last_name': 'Carter',
                'subjects': ['History'],
                'role_type': 'admin'
            },
            {
                'username': 'david_hayes',
                'email': 'david.hayes@example.com',
                'first_name': 'Prof. David',
                'last_name': 'Hayes',
                'subjects': ['English'],
                'role_type': 'subject_teacher'
            },
            {
                'username': 'olivia_foster',
                'email': 'olivia.foster@example.com',
                'first_name': 'Ms. Olivia',
                'last_name': 'Foster',
                'subjects': ['Art'],
                'role_type': 'class_teacher'
            }
        ]
        
        for teacher_data in teachers_data:
            teacher_user, created = User.objects.get_or_create(
                username=teacher_data['username'],
                defaults={
                    'email': teacher_data['email'],
                    'first_name': teacher_data['first_name'],
                    'last_name': teacher_data['last_name'],
                    'role': 'teacher',
                    'mobile_number': '+1-555-' + str(1000 + len(teacher_data['username'])),
                    'city': 'San Francisco',
                    'country': 'United States'
                }
            )
            if created:
                teacher_user.set_password('teacher123')
                teacher_user.save()
            
            # Create teacher profile
            teacher_profile, created = TeacherProfile.objects.get_or_create(
                user=teacher_user,
                school=school,
                defaults={
                    'teacher_role': teacher_data['role_type'],
                    'status': 'active'
                }
            )
            
            # Assign subjects
            for subject_name in teacher_data['subjects']:
                subject = Subject.objects.get(name=subject_name)
                teacher_profile.assigned_subjects.add(subject)
        
        # Create sample environmental project
        project, created = Project.objects.get_or_create(
            title='School Garden Project',
            defaults={
                'short_description': 'Creating sustainable school gardens to teach environmental stewardship.',
                'detailed_description': 'Our school garden project aims to create a sustainable learning environment where students can learn about agriculture, environmental science, and healthy eating while contributing to their school community.',
                'environmental_themes': ['sustainable_agriculture', 'biodiversity'],
                'start_date': date.today(),
                'end_date': date.today() + timedelta(days=180),
                'is_open_for_collaboration': True,
                # goals is not in the schema?
                # 'goals': [
                #     'Plant 500 trees in school grounds',
                #     'Engage 200+ students in environmental activities',
                #     'Reduce school waste by 30%'
                # ],
                'offer_rewards': True,
                'recognition_type': 'Certificate of Environmental Excellence',
                'award_criteria': 'Active participation in all project phases',
                'lead_school': school,
                'contact_person_name': 'Rishabh Bhandari',
                'contact_person_email': 'contact@greenwood.edu',
                'contact_person_role': 'Environmental Coordinator',
                'contact_country': 'United States',
                'contact_city': 'San Francisco',
                'status': 'active',
                'created_by': admin_user
            }
        )
        
        # Create sample environmental impact data
        impacts = [
            {'type': 'trees_planted', 'value': 127, 'unit': 'trees'},
            {'type': 'students_engaged', 'value': 2140, 'unit': 'students'},
            {'type': 'waste_recycled', 'value': 800, 'unit': 'kg'},
            {'type': 'water_saved', 'value': 45000, 'unit': 'liters'},
        ]
        
        for impact_data in impacts:
            EnvironmentalImpact.objects.get_or_create(
                project=project,
                school=school,
                impact_type=impact_data['type'],
                defaults={
                    'value': impact_data['value'],
                    'unit': impact_data['unit'],
                    'measurement_date': date.today(),
                    'verified': True,
                    'notes': f'Sample data for {impact_data["type"]}'
                }
            )
        
        # Create sample donation
        Donation.objects.get_or_create(
            donor_email='sarah.johnson@example.com',
            defaults={
                'donor_name': 'Sarah Johnson',
                'amount': 100.00,
                'payment_method': 'card',
                'purpose': 'trees',
                'recipient_name': 'Michael Anderson',
                'send_ecard': True,
                'recipient_email': 'michael.anderson@example.com',
                'message': 'Your commitment to the environment will help create a greener future for generations to come. Thank you for being a catalyst for change!',
                'payment_status': 'completed'
            }
        )
        
        # Create sample certificate
        Certificate.objects.get_or_create(
            recipient=admin_user,
            defaults={
                'certificate_type': 'honor',
                'title': 'Global Classroom Pool Certificate of Honor',
                'description': 'In honor of Michael Anderson. This donation will help to grow 500 more trees.',
                'project': project,
                'issued_by': admin_user
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully loaded sample data!')
        )
        self.stdout.write('Sample users created:')
        self.stdout.write('- School Admin: school_admin / admin123')
        self.stdout.write('- Teachers: evelyn_carter, charles_bennett, etc. / teacher123')
        self.stdout.write('- School: Greenwood Elementary Academy')
        self.stdout.write('- Project: School Garden Project')
        self.stdout.write('- Environmental impact data and donations loaded')