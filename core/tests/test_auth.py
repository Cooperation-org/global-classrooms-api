from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
import factory

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    username = factory.Sequence(lambda n: f'user{n}')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True

class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.login_url = reverse('token_obtain_pair')
        self.register_url = reverse('register')
        self.valid_payload = {
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'username': 'newuser'
        }
        self.login_payload = {
            'email': self.user.email,
            'password': 'testpass123'
        }

    def test_user_can_register(self):
        """Test that a user can register with valid credentials"""
        response = self.client.post(self.register_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.valid_payload['email']).exists())

    def test_user_cannot_register_with_existing_email(self):
        """Test that a user cannot register with an existing email"""
        # First registration
        self.client.post(self.register_url, self.valid_payload)
        # Second registration with same email
        response = self.client.post(self.register_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_login(self):
        """Test that a user can login with valid credentials"""
        response = self.client.post(self.login_url, self.login_payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_user_cannot_login_with_wrong_password(self):
        """Test that a user cannot login with wrong password"""
        wrong_payload = self.login_payload.copy()
        wrong_payload['password'] = 'wrongpass'
        response = self.client.post(self.login_url, wrong_payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_login_with_unregistered_email(self):
        """Test that a user cannot login with an unregistered email"""
        wrong_payload = self.login_payload.copy()
        wrong_payload['email'] = 'nonexistent@example.com'
        response = self.client.post(self.login_url, wrong_payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) 