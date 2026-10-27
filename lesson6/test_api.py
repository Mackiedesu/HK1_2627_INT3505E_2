import unittest
import json
from app import create_app
from models import db
from seed import seed_database

class SocialNetworkAPITestCase(unittest.TestCase):
    """
    Automated Test Suite for Lesson 6 Social Network API.
    Covers all required endpoints, scopes, errors, and status codes:
    200, 400, 401, 403, 404, 422.
    """

    @classmethod
    def setUpClass(cls):
        """Seed the database once before running tests."""
        seed_database()

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def login(self, email="alice@social.net", password="Password123!"):
        """Helper to login and get token pair."""
        res = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        return res

    # =========================================================================
    # 1. Tests for POST /auth/login
    # =========================================================================
    def test_01_login_success_200(self):
        """Test successful login returning access and refresh tokens (200 OK)."""
        res = self.login("alice@social.net", "Password123!")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["token_type"], "Bearer")
        self.assertEqual(data["expires_in"], 900)

    def test_02_login_bad_request_missing_body_400(self):
        """Test login with missing body or non-JSON payload (400 Bad Request)."""
        res = self.client.post("/api/v1/auth/login", data="not json", content_type="text/plain")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "bad_request")

    def test_03_login_bad_request_missing_fields_400(self):
        """Test login with missing required email or password fields (400 Bad Request)."""
        res = self.client.post("/api/v1/auth/login", json={"email": "alice@social.net"})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "bad_request")

    def test_04_login_validation_error_invalid_email_422(self):
        """Test login with malformed email format (422 Unprocessable Content)."""
        res = self.client.post("/api/v1/auth/login", json={
            "email": "not-an-email-format",
            "password": "Password123!"
        })
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertEqual(data["error"], "validation_error")

    def test_05_login_invalid_password_401(self):
        """Test login with wrong password returns generic 401 error."""
        res = self.login("alice@social.net", "WrongPassword!")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["error"], "invalid_credentials")

    def test_06_login_non_existent_email_401(self):
        """Test login with unregistered email returns generic 401 (Chống User Enumeration)."""
        res = self.login("unknown_user@social.net", "Password123!")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["error"], "invalid_credentials")

    # =========================================================================
    # 2. Tests for POST /auth/refresh
    # =========================================================================
    def test_07_refresh_token_success_200(self):
        """Test exchanging valid refresh token for new access and rotated refresh token (200 OK)."""
        login_res = self.login("alice@social.net", "Password123!")
        tokens = login_res.get_json()
        refresh_token = tokens["refresh_token"]

        res = self.client.post("/api/v1/auth/refresh", headers={
            "Authorization": f"Bearer {refresh_token}"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        # Ensure rotated refresh token is newly minted (different signature)
        self.assertNotEqual(tokens["refresh_token"], data["refresh_token"])

    def test_08_refresh_token_rotation_blocklist_401(self):
        """Test that old refresh token is revoked after rotation (RTR Defense - 401)."""
        login_res = self.login("alice@social.net", "Password123!")
        tokens = login_res.get_json()
        old_refresh_token = tokens["refresh_token"]

        # First refresh: succeeds
        res1 = self.client.post("/api/v1/auth/refresh", headers={
            "Authorization": f"Bearer {old_refresh_token}"
        })
        self.assertEqual(res1.status_code, 200)

        # Second refresh using OLD rotated token: must fail with 401 token_revoked
        res2 = self.client.post("/api/v1/auth/refresh", headers={
            "Authorization": f"Bearer {old_refresh_token}"
        })
        self.assertEqual(res2.status_code, 401)
        data = res2.get_json()
        self.assertEqual(data["error"], "token_revoked")

    def test_09_refresh_with_access_token_rejected_422_or_401(self):
        """Test sending an Access Token instead of Refresh Token to /auth/refresh."""
        login_res = self.login("alice@social.net", "Password123!")
        access_token = login_res.get_json()["access_token"]

        # Flask-JWT-Extended rejects access token on @jwt_required(refresh=True) with 422
        res = self.client.post("/api/v1/auth/refresh", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertIn(res.status_code, [401, 422])

    # =========================================================================
    # 3. Tests for GET /posts/{id}
    # =========================================================================
    def test_10_get_public_post_success_200(self):
        """Test authorized user reading a public post (200 OK)."""
        login_res = self.login("alice@social.net", "Password123!")
        access_token = login_res.get_json()["access_token"]

        res = self.client.get("/api/v1/posts/101", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["id"], 101)
        self.assertEqual(data["visibility"], "public")
        self.assertIn("author", data)
        # Anti-Mass Exposure test: Ensure password_hash is NOT present in response
        self.assertNotIn("password_hash", data["author"])
        self.assertNotIn("password_hash", data)

    def test_11_get_post_bad_request_non_integer_id_400(self):
        """Test passing invalid non-integer ID parameter (400 Bad Request)."""
        login_res = self.login("alice@social.net", "Password123!")
        access_token = login_res.get_json()["access_token"]

        res = self.client.get("/api/v1/posts/abc_invalid", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "bad_request")

    def test_12_get_post_unauthorized_missing_token_401(self):
        """Test reading post without Authorization header (401 Unauthorized)."""
        res = self.client.get("/api/v1/posts/101")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["error"], "missing_token")

    def test_13_get_post_insufficient_scope_403(self):
        """Test user lacking 'posts:read' scope receives 403 Forbidden."""
        # Viewer user has only 'profile:read' scope, lacking 'posts:read'
        login_res = self.login("viewer@social.net", "Password123!")
        access_token = login_res.get_json()["access_token"]

        res = self.client.get("/api/v1/posts/101", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertEqual(data["error"], "insufficient_scope")
        self.assertIn("posts:read", data["need_all_of"])

    def test_14_get_private_post_bola_defense_404(self):
        """
        BOLA Defense Test (OWASP API1:2023):
        User Bob tries to access Alice's private post (Post 102).
        Must be rejected with 404 Not Found to prevent Resource Enumeration.
        """
        login_res = self.login("bob@social.net", "Password123!")
        access_token = login_res.get_json()["access_token"]

        res = self.client.get("/api/v1/posts/102", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["error"], "not_found")

    def test_15_get_private_post_owner_success_200(self):
        """Test owner Alice accessing her own private post (Post 102 - 200 OK)."""
        login_res = self.login("alice@social.net", "Password123!")
        access_token = login_res.get_json()["access_token"]

        res = self.client.get("/api/v1/posts/102", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["id"], 102)
        self.assertEqual(data["visibility"], "private")

    def test_16_get_private_post_admin_bypass_200(self):
        """Test System Administrator accessing Alice's private post (Post 102 - 200 OK)."""
        login_res = self.login("admin@social.net", "AdminPass123!")
        access_token = login_res.get_json()["access_token"]

        res = self.client.get("/api/v1/posts/102", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["id"], 102)

    def test_17_logout_revokes_token_401(self):
        """Test /auth/logout revokes current access token."""
        login_res = self.login("alice@social.net", "Password123!")
        access_token = login_res.get_json()["access_token"]

        # Call logout
        logout_res = self.client.post("/api/v1/auth/logout", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(logout_res.status_code, 200)

        # Call /posts/101 with revoked token -> must fail with 401 token_revoked
        res = self.client.get("/api/v1/posts/101", headers={
            "Authorization": f"Bearer {access_token}"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["error"], "token_revoked")


if __name__ == "__main__":
    unittest.main()
