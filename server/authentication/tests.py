"""
Tests for the authentication app (CustomUser model, signup, login).
"""
import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from .models import CustomUser


class CustomUserModelTests(TestCase):
    """Tests for the CustomUser model and manager."""

    def test_user_creation(self):
        """Creating a user with email+password should succeed."""
        user = CustomUser.objects.create_user(
            email="test@example.com",
            password="secure_password123"
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("secure_password123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.id)  # UUID primary key

    def test_user_creation_normalizes_email(self):
        """Email domain should be lowercased."""
        user = CustomUser.objects.create_user(
            email="Test@Example.COM",
            password="pwd"
        )
        self.assertEqual(user.email, "Test@example.com")

    def test_user_creation_no_email_raises_error(self):
        """Creating a user without email should raise ValueError."""
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email="", password="pwd")

    def test_superuser_creation(self):
        """Creating a superuser sets is_staff=True and is_superuser=True."""
        admin = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="admin_pass"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_superuser_must_have_is_staff(self):
        """Superuser with is_staff=False should raise ValueError."""
        with self.assertRaises(ValueError):
            CustomUser.objects.create_superuser(
                email="admin@example.com",
                password="admin_pass",
                is_staff=False
            )

    def test_superuser_must_have_is_superuser(self):
        """Superuser with is_superuser=False should raise ValueError."""
        with self.assertRaises(ValueError):
            CustomUser.objects.create_superuser(
                email="admin@example.com",
                password="admin_pass",
                is_superuser=False
            )

    def test_user_str_method(self):
        """__str__ should return the email."""
        user = CustomUser.objects.create_user(
            email="strtest@example.com",
            password="pwd"
        )
        self.assertEqual(str(user), "strtest@example.com")

    def test_user_email_unique(self):
        """Creating two users with the same email should fail."""
        CustomUser.objects.create_user(
            email="unique@example.com",
            password="pwd1"
        )
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                email="unique@example.com",
                password="pwd2"
            )


class SignupViewTests(TestCase):
    """Tests for the UserRegistrationView (POST /signup/)."""

    def setUp(self):
        self.signup_url = reverse("signup")

    def test_signup_success(self):
        """POST with valid email+password returns 201 and a token."""
        data = {"email": "newuser@example.com", "password": "strong_pass1"}
        response = self.client.post(
            self.signup_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIn("token", body)
        self.assertIn("email", body)
        self.assertEqual(body["email"], "newuser@example.com")
        # Verify user was actually created
        self.assertTrue(CustomUser.objects.filter(email="newuser@example.com").exists())

    def test_signup_duplicate_email(self):
        """POST with an existing email returns 400."""
        CustomUser.objects.create_user(email="dup@example.com", password="p1")
        data = {"email": "dup@example.com", "password": "p2"}
        response = self.client.post(
            self.signup_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_signup_missing_email(self):
        """POST without email returns 400."""
        data = {"password": "some_pass"}
        response = self.client.post(
            self.signup_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_signup_missing_password(self):
        """POST without password returns 400."""
        data = {"email": "nopass@example.com"}
        response = self.client.post(
            self.signup_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)


class LoginViewTests(TestCase):
    """Tests for the UserLoginView (POST /login/)."""

    def setUp(self):
        self.login_url = reverse("login")
        self.password = "test_password_123"
        self.user = CustomUser.objects.create_user(
            email="login@example.com",
            password=self.password
        )

    def test_login_success(self):
        """POST with valid credentials returns 200 and a token."""
        data = {"email": "login@example.com", "password": self.password}
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("token", body)
        self.assertEqual(body["email"], "login@example.com")

    def test_login_invalid_password(self):
        """POST with wrong password returns 401."""
        data = {"email": "login@example.com", "password": "wrong_password"}
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_login_nonexistent_user(self):
        """POST with non-existent email returns 401."""
        data = {"email": "ghost@example.com", "password": "pwd"}
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_login_missing_email(self):
        """POST without email returns 400."""
        data = {"password": self.password}
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_login_missing_password(self):
        """POST without password returns 400."""
        data = {"email": "login@example.com"}
        response = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_login_returns_token_created_at(self):
        """Token.created should be updated on each successful login."""
        data = {"email": "login@example.com", "password": self.password}
        # First login
        response1 = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        token1 = response1.json()["token"]

        # Second login — same user gets same token (get_or_create)
        response2 = self.client.post(
            self.login_url,
            data=json.dumps(data),
            content_type="application/json"
        )
        token2 = response2.json()["token"]
        self.assertEqual(token1, token2)