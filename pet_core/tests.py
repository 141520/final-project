from unittest.mock import Mock, patch

import jwt
from django.test import SimpleTestCase, override_settings

from .middleware import SupabaseAuthMiddleware
from .models import normalize_external_link


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
