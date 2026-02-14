"""
Unit Tests for User Authentication
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistration:
    """Test user registration endpoints"""

    def setup_method(self):
        self.client = APIClient()

    def test_rider_registration_success(self):
        """Test successful rider registration"""
        data = {
            "phone": "9876543210",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "Rider",
            "email": "rider@test.com"
        }
        
        response = self.client.post("/api/users/register/", data, format="json")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["phone"] == "9876543210"
        assert response.data["role"] == "rider"
        
        # Verify user was created
        user = User.objects.get(phone="9876543210")
        assert user.first_name == "Test"

    def test_driver_registration_success(self):
        """Test successful driver registration"""
        data = {
            "phone": "1234567890",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "Driver",
            "role": "driver"
        }
        
        response = self.client.post("/api/users/register/", data, format="json")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["role"] == "driver"

    def test_registration_duplicate_phone(self):
        """Test registration with duplicate phone number"""
        User.objects.create_user(
            username="existing",
            phone="9876543210",
            password="pass123"
        )
        
        data = {
            "phone": "9876543210",
            "password": "newpass123",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = self.client.post("/api/users/register/", data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Test user login endpoints"""

    def setup_method(self):
        self.client = APIClient()
        self.rider = User.objects.create_user(
            username="rider",
            phone="9876543210",
            password="testpass123",
            role="rider"
        )
        self.driver = User.objects.create_user(
            username="driver",
            phone="1234567890",
            password="testpass123",
            role="driver"
        )

    def test_rider_login_success(self):
        """Test successful rider login"""
        data = {
            "phone": "9876543210",
            "password": "testpass123"
        }
        
        response = self.client.post("/api/users/login/", data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["phone"] == "9876543210"

    def test_driver_login_success(self):
        """Test successful driver login"""
        data = {
            "phone": "1234567890",
            "password": "testpass123"
        }
        
        response = self.client.post("/api/users/driver-login/", data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert response.data["user"]["role"] == "driver"

    def test_login_wrong_password(self):
        """Test login with wrong password"""
        data = {
            "phone": "9876543210",
            "password": "wrongpassword"
        }
        
        response = self.client.post("/api/users/login/", data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
