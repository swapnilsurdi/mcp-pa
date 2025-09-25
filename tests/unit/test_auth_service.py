"""
Unit tests for authentication service
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import jwt

from src.auth_service import (
    UserContext,
    AuthenticationError,
    AuthorizationError,
    OAuthProvider,
    JWTAuth,
    APIKeyAuth,
    AuthService,
    create_auth_service
)


class TestUserContext:
    """Test UserContext dataclass"""
    
    def test_user_context_creation(self):
        """Test basic user context creation"""
        user = UserContext(
            user_id="test_user",
            email="test@example.com",
            tenant_id="test_tenant"
        )
        
        assert user.user_id == "test_user"
        assert user.email == "test@example.com"
        assert user.tenant_id == "test_tenant"
        assert user.permissions == ["read", "write"]  # Default permissions
        assert user.metadata == {}  # Default metadata
    
    def test_user_context_with_custom_values(self):
        """Test user context with custom permissions and metadata"""
        user = UserContext(
            user_id="admin_user",
            email="admin@example.com",
            name="Admin User",
            tenant_id="admin_tenant",
            permissions=["read", "write", "admin", "delete"],
            metadata={"role": "admin", "department": "IT"}
        )
        
        assert user.name == "Admin User"
        assert "admin" in user.permissions
        assert user.metadata["role"] == "admin"


class TestOAuthProvider:
    """Test OAuthProvider class"""
    
    @pytest.fixture
    def oauth_config(self):
        """OAuth configuration fixture"""
        return {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "issuer": "https://auth.example.com"
        }
    
    def test_oauth_provider_init(self, oauth_config):
        """Test OAuth provider initialization"""
        provider = OAuthProvider(
            oauth_config["client_id"],
            oauth_config["client_secret"], 
            oauth_config["issuer"]
        )
        
        assert provider.client_id == oauth_config["client_id"]
        assert provider.client_secret == oauth_config["client_secret"]
        assert provider.issuer == oauth_config["issuer"]
        assert provider._discovery_cache is None
    
    @pytest.mark.asyncio
    async def test_get_discovery_document(self, oauth_config):
        """Test fetching OAuth discovery document"""
        provider = OAuthProvider(**oauth_config)
        
        mock_discovery = {
            "issuer": oauth_config["issuer"],
            "authorization_endpoint": "https://auth.example.com/auth",
            "token_endpoint": "https://auth.example.com/token",
            "jwks_uri": "https://auth.example.com/jwks"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_discovery
            mock_response.raise_for_status.return_value = None
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            discovery = await provider.get_discovery_document()
            
            assert discovery == mock_discovery
            assert provider._discovery_cache == mock_discovery
    
    @pytest.mark.asyncio
    async def test_get_discovery_document_cached(self, oauth_config):
        """Test cached discovery document retrieval"""
        provider = OAuthProvider(**oauth_config)
        
        # Set cache
        cached_discovery = {"issuer": oauth_config["issuer"]}
        provider._discovery_cache = cached_discovery
        provider._cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        with patch('httpx.AsyncClient') as mock_client:
            # Should not make HTTP request
            discovery = await provider.get_discovery_document()
            
            assert discovery == cached_discovery
            assert not mock_client.called
    
    @pytest.mark.asyncio
    async def test_get_jwks(self, oauth_config):
        """Test fetching JWKS"""
        provider = OAuthProvider(**oauth_config)
        
        mock_discovery = {
            "jwks_uri": "https://auth.example.com/jwks"
        }
        mock_jwks = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "test_key_id",
                    "use": "sig",
                    "n": "test_n",
                    "e": "AQAB"
                }
            ]
        }
        
        with patch.object(provider, 'get_discovery_document', return_value=mock_discovery):
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_jwks
                mock_response.raise_for_status.return_value = None
                
                mock_client_instance = AsyncMock()
                mock_client_instance.get.return_value = mock_response
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                jwks = await provider.get_jwks()
                
                assert jwks == mock_jwks
    
    def test_derive_tenant_id(self, oauth_config):
        """Test tenant ID derivation from email"""
        provider = OAuthProvider(**oauth_config)
        
        # Test corporate email
        tenant_id = provider._derive_tenant_id("user@company.com")
        assert tenant_id == "company_com"
        
        # Test personal email
        tenant_id = provider._derive_tenant_id("user@gmail.com")
        assert tenant_id == "personal"
        
        # Test no email
        tenant_id = provider._derive_tenant_id(None)
        assert tenant_id == "default"
        
        # Test malformed email
        tenant_id = provider._derive_tenant_id("invalid_email")
        assert tenant_id == "default"
    
    def test_extract_permissions(self, oauth_config):
        """Test permission extraction from OAuth claims"""
        provider = OAuthProvider(**oauth_config)
        
        # Test admin role
        claims = {"roles": ["admin"]}
        permissions = provider._extract_permissions(claims)
        assert "admin" in permissions
        assert "read" in permissions
        assert "write" in permissions
        
        # Test user role
        claims = {"roles": ["user"]}
        permissions = provider._extract_permissions(claims)
        assert "read" in permissions
        assert "write" in permissions
        assert "admin" not in permissions
        
        # Test direct permissions
        claims = {"permissions": ["read", "special_permission"]}
        permissions = provider._extract_permissions(claims)
        assert "read" in permissions
        assert "special_permission" in permissions
        
        # Test no roles or permissions
        claims = {}
        permissions = provider._extract_permissions(claims)
        assert permissions == ["read", "write"]  # Default permissions
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, oauth_config):
        """Test successful token verification"""
        provider = OAuthProvider(**oauth_config)
        
        mock_claims = {
            "iss": oauth_config["issuer"],
            "aud": oauth_config["client_id"],
            "sub": "user123",
            "email": "user@company.com",
            "name": "Test User",
            "roles": ["user"],
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp())
        }
        
        with patch.object(provider, 'get_jwks', return_value={}):
            with patch('authlib.jose.jwt.decode', return_value=mock_claims):
                user = await provider.verify_token("valid_token")
                
                assert user.user_id == "user123"
                assert user.email == "user@company.com"
                assert user.name == "Test User"
                assert user.tenant_id == "company_com"
                assert "read" in user.permissions
                assert "write" in user.permissions
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid_issuer(self, oauth_config):
        """Test token verification with invalid issuer"""
        provider = OAuthProvider(**oauth_config)
        
        mock_claims = {
            "iss": "https://malicious.com",
            "aud": oauth_config["client_id"],
            "sub": "user123"
        }
        
        with patch.object(provider, 'get_jwks', return_value={}):
            with patch('authlib.jose.jwt.decode', return_value=mock_claims):
                with pytest.raises(AuthenticationError, match="Invalid issuer"):
                    await provider.verify_token("invalid_token")
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid_audience(self, oauth_config):
        """Test token verification with invalid audience"""
        provider = OAuthProvider(**oauth_config)
        
        mock_claims = {
            "iss": oauth_config["issuer"],
            "aud": "wrong_client_id",
            "sub": "user123"
        }
        
        with patch.object(provider, 'get_jwks', return_value={}):
            with patch('authlib.jose.jwt.decode', return_value=mock_claims):
                with pytest.raises(AuthenticationError, match="Invalid audience"):
                    await provider.verify_token("invalid_token")


class TestJWTAuth:
    """Test JWTAuth class"""
    
    @pytest.fixture
    def jwt_secret(self):
        """JWT secret fixture"""
        return "super_secret_key_for_testing"
    
    def test_jwt_auth_init(self, jwt_secret):
        """Test JWT auth initialization"""
        jwt_auth = JWTAuth(jwt_secret, algorithm="HS256", expiry_hours=24)
        
        assert jwt_auth.secret == jwt_secret
        assert jwt_auth.algorithm == "HS256"
        assert jwt_auth.expiry_hours == 24
    
    def test_create_token(self, jwt_secret):
        """Test JWT token creation"""
        jwt_auth = JWTAuth(jwt_secret)
        
        user = UserContext(
            user_id="test_user",
            email="test@example.com",
            name="Test User",
            tenant_id="test_tenant",
            permissions=["read", "write"]
        )
        
        token = jwt_auth.create_token(user)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == "test_user"
        assert payload["email"] == "test@example.com"
        assert payload["tenant_id"] == "test_tenant"
    
    def test_verify_token_success(self, jwt_secret):
        """Test successful JWT token verification"""
        jwt_auth = JWTAuth(jwt_secret)
        
        user = UserContext(
            user_id="test_user",
            email="test@example.com",
            tenant_id="test_tenant",
            permissions=["read", "admin"]
        )
        
        token = jwt_auth.create_token(user)
        verified_user = jwt_auth.verify_token(token)
        
        assert verified_user.user_id == user.user_id
        assert verified_user.email == user.email
        assert verified_user.tenant_id == user.tenant_id
        assert verified_user.permissions == user.permissions
    
    def test_verify_token_expired(self, jwt_secret):
        """Test verification of expired JWT token"""
        jwt_auth = JWTAuth(jwt_secret, expiry_hours=0)  # Immediate expiry
        
        user = UserContext(
            user_id="test_user",
            email="test@example.com",
            tenant_id="test_tenant"
        )
        
        # Create token that expires immediately
        import time
        time.sleep(1)  # Ensure token is expired
        
        expired_payload = {
            "sub": user.user_id,
            "email": user.email,
            "tenant_id": user.tenant_id,
            "exp": int((datetime.now() - timedelta(hours=1)).timestamp())
        }
        expired_token = jwt.encode(expired_payload, jwt_secret, algorithm="HS256")
        
        with pytest.raises(AuthenticationError, match="Token expired"):
            jwt_auth.verify_token(expired_token)
    
    def test_verify_token_invalid(self, jwt_secret):
        """Test verification of invalid JWT token"""
        jwt_auth = JWTAuth(jwt_secret)
        
        with pytest.raises(AuthenticationError, match="Invalid token"):
            jwt_auth.verify_token("invalid_token_format")
    
    def test_verify_token_wrong_secret(self, jwt_secret):
        """Test verification with wrong secret"""
        jwt_auth = JWTAuth(jwt_secret)
        wrong_jwt_auth = JWTAuth("wrong_secret")
        
        user = UserContext(
            user_id="test_user",
            email="test@example.com",
            tenant_id="test_tenant"
        )
        
        token = jwt_auth.create_token(user)
        
        with pytest.raises(AuthenticationError, match="Invalid token"):
            wrong_jwt_auth.verify_token(token)


class TestAPIKeyAuth:
    """Test APIKeyAuth class"""
    
    def test_api_key_auth_init(self):
        """Test API key auth initialization"""
        api_keys = {
            "key1": UserContext(user_id="user1", email="user1@example.com", tenant_id="tenant1"),
            "key2": UserContext(user_id="user2", email="user2@example.com", tenant_id="tenant2")
        }
        
        auth = APIKeyAuth(api_keys)
        assert auth.api_keys == api_keys
    
    def test_verify_api_key_success(self):
        """Test successful API key verification"""
        user = UserContext(
            user_id="api_user",
            email="api@example.com",
            tenant_id="api_tenant"
        )
        
        auth = APIKeyAuth({"valid_key": user})
        
        verified_user = auth.verify_api_key("valid_key")
        assert verified_user == user
    
    def test_verify_api_key_invalid(self):
        """Test invalid API key verification"""
        auth = APIKeyAuth({"valid_key": UserContext("user", "email", "tenant")})
        
        with pytest.raises(AuthenticationError, match="Invalid API key"):
            auth.verify_api_key("invalid_key")
    
    def test_from_key_list(self):
        """Test creating APIKeyAuth from key list"""
        keys = ["key1", "key2", "key3"]
        
        auth = APIKeyAuth.from_key_list(keys)
        
        assert len(auth.api_keys) == 3
        assert "key1" in auth.api_keys
        assert "key2" in auth.api_keys
        assert "key3" in auth.api_keys
        
        # Verify generated user contexts
        user1 = auth.api_keys["key1"]
        assert user1.user_id == "api_user_0"
        assert user1.email == "api_user_0@system.local"
        assert user1.tenant_id == "api"


class TestAuthService:
    """Test AuthService class"""
    
    @pytest.fixture
    def mock_oauth_provider(self):
        """Mock OAuth provider"""
        provider = MagicMock(spec=OAuthProvider)
        provider.verify_token = AsyncMock(return_value=UserContext(
            user_id="oauth_user",
            email="oauth@example.com",
            tenant_id="oauth_tenant"
        ))
        return provider
    
    @pytest.fixture
    def mock_jwt_auth(self):
        """Mock JWT auth"""
        auth = MagicMock(spec=JWTAuth)
        auth.verify_token = MagicMock(return_value=UserContext(
            user_id="jwt_user",
            email="jwt@example.com",
            tenant_id="jwt_tenant"
        ))
        return auth
    
    @pytest.fixture
    def mock_api_key_auth(self):
        """Mock API key auth"""
        auth = MagicMock(spec=APIKeyAuth)
        auth.verify_api_key = MagicMock(return_value=UserContext(
            user_id="api_user",
            email="api@example.com",
            tenant_id="api_tenant"
        ))
        return auth
    
    @pytest.mark.asyncio
    async def test_authenticate_oauth(self, mock_oauth_provider):
        """Test OAuth authentication"""
        service = AuthService(oauth_provider=mock_oauth_provider)
        
        user = await service.authenticate("oauth_token", auth_type="oauth")
        
        assert user.user_id == "oauth_user"
        mock_oauth_provider.verify_token.assert_called_once_with("oauth_token")
    
    @pytest.mark.asyncio
    async def test_authenticate_jwt(self, mock_jwt_auth):
        """Test JWT authentication"""
        service = AuthService(jwt_auth=mock_jwt_auth)
        
        user = await service.authenticate("jwt_token", auth_type="jwt")
        
        assert user.user_id == "jwt_user"
        mock_jwt_auth.verify_token.assert_called_once_with("jwt_token")
    
    @pytest.mark.asyncio
    async def test_authenticate_api_key(self, mock_api_key_auth):
        """Test API key authentication"""
        service = AuthService(api_key_auth=mock_api_key_auth)
        
        user = await service.authenticate("api_key", auth_type="api_key")
        
        assert user.user_id == "api_user"
        mock_api_key_auth.verify_api_key.assert_called_once_with("api_key")
    
    @pytest.mark.asyncio
    async def test_authenticate_auto_oauth_first(self, mock_oauth_provider, mock_jwt_auth):
        """Test auto authentication with OAuth succeeding first"""
        service = AuthService(oauth_provider=mock_oauth_provider, jwt_auth=mock_jwt_auth)
        
        user = await service.authenticate("token", auth_type="auto")
        
        assert user.user_id == "oauth_user"
        mock_oauth_provider.verify_token.assert_called_once()
        mock_jwt_auth.verify_token.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_authenticate_auto_fallback(self, mock_jwt_auth):
        """Test auto authentication with fallback"""
        # Mock OAuth to fail
        mock_oauth_provider = MagicMock(spec=OAuthProvider)
        mock_oauth_provider.verify_token = AsyncMock(
            side_effect=AuthenticationError("OAuth failed")
        )
        
        service = AuthService(oauth_provider=mock_oauth_provider, jwt_auth=mock_jwt_auth)
        
        user = await service.authenticate("token", auth_type="auto")
        
        assert user.user_id == "jwt_user"
        mock_oauth_provider.verify_token.assert_called_once()
        mock_jwt_auth.verify_token.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_no_providers(self):
        """Test authentication with no providers configured"""
        service = AuthService()
        
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await service.authenticate("token")
    
    def test_check_permission(self):
        """Test permission checking"""
        service = AuthService()
        
        user = UserContext(
            user_id="user",
            email="user@example.com",
            tenant_id="tenant",
            permissions=["read", "write"]
        )
        
        assert service.check_permission(user, "read") is True
        assert service.check_permission(user, "write") is True
        assert service.check_permission(user, "admin") is False
    
    def test_require_permission_success(self):
        """Test requiring permission successfully"""
        service = AuthService()
        
        user = UserContext(
            user_id="user",
            email="user@example.com",
            tenant_id="tenant",
            permissions=["read", "admin"]
        )
        
        # Should not raise exception
        service.require_permission(user, "admin")
    
    def test_require_permission_failure(self):
        """Test requiring permission failure"""
        service = AuthService()
        
        user = UserContext(
            user_id="user",
            email="user@example.com",
            tenant_id="tenant",
            permissions=["read"]
        )
        
        with pytest.raises(AuthorizationError, match="Permission 'admin' required"):
            service.require_permission(user, "admin")


class TestCreateAuthService:
    """Test create_auth_service function"""
    
    def test_create_auth_service_disabled(self):
        """Test creating auth service when disabled"""
        config = MagicMock()
        config.enabled = False
        
        service = create_auth_service(config)
        assert service is None
    
    def test_create_auth_service_oauth(self):
        """Test creating auth service with OAuth"""
        config = MagicMock()
        config.enabled = True
        config.provider = "oauth"
        config.oauth_client_id = "test_client"
        config.oauth_client_secret = "test_secret"
        config.oauth_issuer = "https://auth.example.com"
        config.jwt_secret = None
        config.api_keys = []
        
        service = create_auth_service(config)
        
        assert service is not None
        assert service.oauth_provider is not None
        assert service.jwt_auth is None
        assert service.api_key_auth is None
    
    def test_create_auth_service_jwt(self):
        """Test creating auth service with JWT"""
        config = MagicMock()
        config.enabled = True
        config.provider = "jwt"
        config.oauth_client_id = None
        config.oauth_client_secret = None
        config.oauth_issuer = None
        config.jwt_secret = "test_secret"
        config.api_keys = []
        
        service = create_auth_service(config)
        
        assert service is not None
        assert service.oauth_provider is None
        assert service.jwt_auth is not None
        assert service.api_key_auth is None
    
    def test_create_auth_service_api_keys(self):
        """Test creating auth service with API keys"""
        config = MagicMock()
        config.enabled = True
        config.provider = "api_key"
        config.oauth_client_id = None
        config.oauth_client_secret = None
        config.oauth_issuer = None
        config.jwt_secret = None
        config.api_keys = ["key1", "key2"]
        
        service = create_auth_service(config)
        
        assert service is not None
        assert service.oauth_provider is None
        assert service.jwt_auth is None
        assert service.api_key_auth is not None
    
    def test_create_auth_service_multiple_providers(self):
        """Test creating auth service with multiple providers"""
        config = MagicMock()
        config.enabled = True
        config.provider = "oauth"
        config.oauth_client_id = "test_client"
        config.oauth_client_secret = "test_secret"
        config.oauth_issuer = "https://auth.example.com"
        config.jwt_secret = "jwt_secret"
        config.api_keys = ["api_key1"]
        
        service = create_auth_service(config)
        
        assert service is not None
        assert service.oauth_provider is not None
        assert service.jwt_auth is not None
        assert service.api_key_auth is not None