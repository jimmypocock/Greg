"""
Pytest fixtures for API integration tests.

Tests run against a live API server. Start the server with:
    uv run greg dev
"""

import os
import pytest
import requests
import time
import uuid

# API configuration - use port 8081 for songwriter app
API_BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8081")


@pytest.fixture(scope="session")
def api_url() -> str:
    """Get API base URL."""
    return API_BASE_URL


@pytest.fixture(scope="session", autouse=True)
def ensure_api_running(api_url):
    """Ensure API is running before tests."""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"\n✓ API is running at {api_url}")
        else:
            pytest.exit(f"API returned status {response.status_code}", returncode=1)
    except requests.exceptions.RequestException as e:
        pytest.exit(
            f"API not accessible at {api_url}. Start with 'uv run greg dev': {e}",
            returncode=1,
        )


@pytest.fixture(scope="function")
def unique_email():
    """Generate a unique email for each test."""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture(scope="function")
def test_password():
    """Standard test password."""
    return "testpassword123"


@pytest.fixture(scope="function")
def registered_user(api_url, unique_email, test_password):
    """
    Register a test user and return credentials.

    Note: First user becomes admin, subsequent users need invite codes.
    Tests should handle both cases.
    """
    user_data = {
        "email": unique_email,
        "password": test_password,
        "invite_code": "",
    }

    response = requests.post(f"{api_url}/auth/register", json=user_data, timeout=10)

    # If registration fails due to invite code requirement, skip
    if response.status_code in [400, 403]:
        detail = response.json().get("detail", "")
        if "invite" in detail.lower():
            pytest.skip("User registration requires invite code (not first user)")

    if response.status_code != 201:
        pytest.fail(f"Registration failed: {response.status_code} - {response.text}")

    return {
        "email": unique_email,
        "password": test_password,
        "user": response.json(),
    }


@pytest.fixture(scope="function")
def auth_tokens(api_url, registered_user):
    """Login and return access/refresh tokens."""
    login_data = {
        "email": registered_user["email"],
        "password": registered_user["password"],
    }

    response = requests.post(f"{api_url}/auth/token", json=login_data, timeout=10)

    if response.status_code != 200:
        pytest.fail(f"Login failed: {response.status_code} - {response.text}")

    tokens = response.json()

    # Handle 2FA if enabled
    if tokens.get("requires_2fa"):
        pytest.skip("User has 2FA enabled, skipping")

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "user": registered_user,
    }


@pytest.fixture(scope="function")
def auth_headers(auth_tokens):
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}


@pytest.fixture(scope="function")
def admin_user(api_url):
    """
    Get or create an admin user.

    Returns None if database already has users (can't create admin).
    """
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    admin_password = "adminpassword123"

    response = requests.post(
        f"{api_url}/auth/register",
        json={
            "email": admin_email,
            "password": admin_password,
            "invite_code": "",
        },
        timeout=10,
    )

    if response.status_code == 201:
        user_data = response.json()
        if user_data.get("is_superuser"):
            # Login to get tokens
            login_response = requests.post(
                f"{api_url}/auth/token",
                json={"email": admin_email, "password": admin_password},
                timeout=10,
            )
            if login_response.status_code == 200:
                tokens = login_response.json()
                return {
                    "email": admin_email,
                    "password": admin_password,
                    "user": user_data,
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                }

    return None
