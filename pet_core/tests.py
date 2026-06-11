from unittest.mock import Mock, patch

import jwt
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import SimpleTestCase, override_settings

from .middleware import SecurityHeadersMiddleware, SupabaseAuthMiddleware
from django.core.exceptions import ValidationError

from .models import (
    normalize_external_link,
    validate_product_external_link,
    POST_TYPE_LOST,
    POST_TYPE_FOUND,
    STATUS_ACTIVE,
    STATUS_RESOLVED,
)
from .views import _validate_image_files, _client_ip, _clean_social_link


class NormalizeExternalLinkTests(SimpleTestCase):
    def test_shopee_product_url_is_canonicalized(self):
        raw = (
            'https://shopee.co.th/name-i.799934388.22758121851'
            '?extraParams=x&sp_atk=tracking'
        )

        self.assertEqual(
            normalize_external_link(raw),
            'https://shopee.co.th/product/799934388/22758121851',
        )

    def test_non_shopee_url_is_only_stripped(self):
        self.assertEqual(
            normalize_external_link('  https://example.com/product?a=1  '),
            'https://example.com/product?a=1',
        )

    def test_product_link_rejects_unknown_domains(self):
        with self.assertRaises(ValidationError):
            validate_product_external_link('https://evil.example/phishing')

    def test_product_link_allows_known_marketplaces(self):
        validate_product_external_link('https://shopee.co.th/product/799934388/22758121851')
        validate_product_external_link('https://www.lazada.co.th/products/example.html')


class SupabaseAuthMiddlewareTests(SimpleTestCase):
    jwt_secret = 'test-secret-with-more-than-32-bytes'

    @override_settings(
        SUPABASE_URL='https://example.supabase.co',
        SUPABASE_ANON_KEY='anon-key',
    )
    @patch('pet_core.middleware.PyJWKClient')
    def test_verified_jwks_claims_are_used(self, jwks_client_cls):
        token = jwt.encode(
            {'sub': 'user-123', 'email': 'a@example.com', 'iss': 'https://example.supabase.co/auth/v1'},
            self.jwt_secret,
            algorithm='HS256',
        )
        signing_key = Mock()
        signing_key.key = self.jwt_secret
        jwks_client_cls.return_value.get_signing_key_from_jwt.return_value = signing_key

        payload = SupabaseAuthMiddleware(lambda request: None)._decode_verified_token(token)

        self.assertEqual(payload['sub'], 'user-123')

    @override_settings(
        SUPABASE_URL='https://example.supabase.co',
        SUPABASE_ANON_KEY='anon-key',
    )
    @patch('pet_core.middleware.requests.get')
    @patch('pet_core.middleware.PyJWKClient')
    def test_legacy_token_falls_back_to_auth_server_verification(self, jwks_client_cls, requests_get):
        token = jwt.encode(
            {'sub': 'legacy-user', 'email': 'legacy@example.com'},
            self.jwt_secret,
            algorithm='HS256',
        )
        jwks_client_cls.return_value.get_signing_key_from_jwt.side_effect = Exception('no jwks')
        response = Mock()
        response.status_code = 200
        response.json.return_value = {'id': 'legacy-user', 'email': 'legacy@example.com'}
        requests_get.return_value = response

        payload = SupabaseAuthMiddleware(lambda request: None)._decode_verified_token(token)

        self.assertEqual(payload['sub'], 'legacy-user')
        requests_get.assert_called_once()

    @override_settings(
        SUPABASE_URL='https://example.supabase.co',
        SUPABASE_ANON_KEY='anon-key',
    )
    @patch('pet_core.middleware.requests.get')
    @patch('pet_core.middleware.PyJWKClient')
    def test_rejected_auth_server_token_returns_none(self, jwks_client_cls, requests_get):
        token = jwt.encode({'sub': 'bad-user'}, self.jwt_secret, algorithm='HS256')
        jwks_client_cls.return_value.get_signing_key_from_jwt.side_effect = Exception('no jwks')
        response = Mock()
        response.status_code = 401
        requests_get.return_value = response

        self.assertIsNone(SupabaseAuthMiddleware(lambda request: None)._decode_verified_token(token))


class UploadValidationTests(SimpleTestCase):
    def test_rejects_oversized_image_before_processing(self):
        upload = SimpleUploadedFile(
            'large.jpg',
            b'x' * (8 * 1024 * 1024 + 1),
            content_type='image/jpeg',
        )

        with self.assertRaises(ValidationError):
            _validate_image_files([upload])

    def test_rejects_non_image_content_type(self):
        upload = SimpleUploadedFile('file.txt', b'hello', content_type='text/plain')

        with self.assertRaises(ValidationError):
            _validate_image_files([upload])


class SecurityHeadersMiddlewareTests(SimpleTestCase):
    def test_adds_content_security_policy(self):
        response = SecurityHeadersMiddleware(lambda request: HttpResponse('ok')).process_response(
            Mock(),
            HttpResponse('ok'),
        )

        self.assertIn('Content-Security-Policy', response)
        self.assertIn("default-src 'self'", response['Content-Security-Policy'])


class ClientIPTests(SimpleTestCase):
    """Test anti-spoof IP resolution"""

    def _req(self, xff='', remote=''):
        r = Mock()
        r.META = {'HTTP_X_FORWARDED_FOR': xff, 'REMOTE_ADDR': remote}
        return r

    def test_uses_last_xff_entry_not_first(self):
        # Spoofed: client sent X-Forwarded-For: 1.1.1.1, but proxy appended real IP 9.9.9.9
        self.assertEqual(_client_ip(self._req(xff='1.1.1.1, 9.9.9.9')), '9.9.9.9')

    def test_falls_back_to_remote_addr(self):
        self.assertEqual(_client_ip(self._req(remote='10.0.0.1')), '10.0.0.1')

    def test_unknown_when_no_data(self):
        self.assertEqual(_client_ip(self._req()), 'unknown')


class SocialLinkValidationTests(SimpleTestCase):
    """Test social_link whitelist"""

    def test_accepts_facebook(self):
        self.assertEqual(
            _clean_social_link('https://facebook.com/user/post/123'),
            'https://facebook.com/user/post/123',
        )

    def test_accepts_instagram_subdomain(self):
        self.assertEqual(
            _clean_social_link('https://www.instagram.com/p/abc'),
            'https://www.instagram.com/p/abc',
        )

    def test_rejects_malicious_url(self):
        self.assertEqual(_clean_social_link('https://evil.example.com/phish'), '')

    def test_rejects_lookalike_domain(self):
        self.assertEqual(_clean_social_link('https://facebook.com.evil.com/'), '')

    def test_empty_string_passes_through(self):
        self.assertEqual(_clean_social_link(''), '')


class ConstantsTests(SimpleTestCase):
    """Sanity check that named constants match the strings used in DB"""

    def test_post_type_values(self):
        self.assertEqual(POST_TYPE_LOST, 'lost')
        self.assertEqual(POST_TYPE_FOUND, 'found')

    def test_status_values(self):
        self.assertEqual(STATUS_ACTIVE, 'active')
        self.assertEqual(STATUS_RESOLVED, 'resolved')
