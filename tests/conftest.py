"""
Open-Monitor Test Configuration
Pytest fixtures and configuration for testing.
"""
import os
import pytest
import tempfile
from datetime import datetime, timezone
from typing import Generator, Dict, Any

# Set testing environment before imports
os.environ['FLASK_ENV'] = 'testing'
os.environ['TESTING'] = 'true'


@pytest.fixture(scope='session')
def app():
    """
    Create application for testing.
    
    Scope: session (one app for all tests)
    """
    from app import create_app
    from app.extensions import db
    
    # Create temp database files
    core_db_fd, core_db_path = tempfile.mkstemp(suffix='.db')
    public_db_fd, public_db_path = tempfile.mkstemp(suffix='.db')
    
    test_config = {
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-not-for-production',
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{core_db_path}',
        'SQLALCHEMY_BINDS': {
            'core': f'sqlite:///{core_db_path}',
            'public': f'sqlite:///{public_db_path}',
        },
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'BCRYPT_LOG_ROUNDS': 4,  # Faster hashing for tests
        'LOGIN_DISABLED': False,
        'SESSION_COOKIE_SECURE': False,
        'ENCRYPTION_KEY': 'gAAAAABnXYZ12345678901234567890123456789012345678901234567890123456789012345678=',
        'AUDIT_LOG_TO_DB': False,  # Disable DB audit logging in tests
        'CSP_ENABLED': False,  # Disable CSP in tests
        'HSTS_ENABLED': False,
    }
    
    app = create_app(test_config)
    
    # Create tables
    with app.app_context():
        db.create_all()
        _create_test_roles(db)
    
    yield app
    
    # Cleanup
    with app.app_context():
        db.drop_all()
    
    os.close(core_db_fd)
    os.close(public_db_fd)
    os.unlink(core_db_path)
    os.unlink(public_db_path)


def _create_test_roles(db):
    """Create default roles for testing."""
    from app.models.auth import Role
    
    roles = [
        ('ADMIN', 'Administrator with full access'),
        ('ANALYST', 'Security analyst with read/write access'),
        ('VIEWER', 'Read-only access to data'),
        ('API_USER', 'API access only'),
    ]
    
    for name, description in roles:
        if not Role.query.filter_by(name=name).first():
            role = Role(name=name, description=description)
            db.session.add(role)
    
    db.session.commit()


@pytest.fixture(scope='function')
def client(app):
    """
    Create test client.
    
    Scope: function (new client for each test)
    """
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    """
    Database fixture with transaction rollback.
    
    Each test runs in a transaction that gets rolled back.
    """
    from app.extensions import db as _db
    
    with app.app_context():
        _db.session.begin_nested()
        
        yield _db
        
        _db.session.rollback()


@pytest.fixture(scope='function')
def session(db):
    """Database session fixture."""
    return db.session


@pytest.fixture
def admin_user(db):
    """Create admin user for testing."""
    from app.models.auth import User, Role
    
    admin_role = Role.query.filter_by(name='ADMIN').first()
    
    user = User(
        username='admin_test',
        email='admin@test.com',
        is_active=True,
        is_admin=True,
    )
    user.set_password('Admin123!@#Test')
    
    if admin_role:
        user.roles.append(admin_role)
    
    db.session.add(user)
    db.session.commit()
    
    return user


@pytest.fixture
def analyst_user(db):
    """Create analyst user for testing."""
    from app.models.auth import User, Role
    
    analyst_role = Role.query.filter_by(name='ANALYST').first()
    
    user = User(
        username='analyst_test',
        email='analyst@test.com',
        is_active=True,
        is_admin=False,
    )
    user.set_password('Analyst123!@#Test')
    
    if analyst_role:
        user.roles.append(analyst_role)
    
    db.session.add(user)
    db.session.commit()
    
    return user


@pytest.fixture
def viewer_user(db):
    """Create viewer user for testing."""
    from app.models.auth import User, Role
    
    viewer_role = Role.query.filter_by(name='VIEWER').first()
    
    user = User(
        username='viewer_test',
        email='viewer@test.com',
        is_active=True,
        is_admin=False,
    )
    user.set_password('Viewer123!@#Test')
    
    if viewer_role:
        user.roles.append(viewer_role)
    
    db.session.add(user)
    db.session.commit()
    
    return user


@pytest.fixture
def inactive_user(db):
    """Create inactive user for testing."""
    from app.models.auth import User
    
    user = User(
        username='inactive_test',
        email='inactive@test.com',
        is_active=False,
        is_admin=False,
    )
    user.set_password('Inactive123!@#Test')
    
    db.session.add(user)
    db.session.commit()
    
    return user


@pytest.fixture
def locked_user(db):
    """Create locked user for testing."""
    from app.models.auth import User
    
    user = User(
        username='locked_test',
        email='locked@test.com',
        is_active=True,
        is_admin=False,
        failed_login_attempts=5,
        locked_until=datetime(2099, 12, 31, tzinfo=timezone.utc),
    )
    user.set_password('Locked123!@#Test')
    
    db.session.add(user)
    db.session.commit()
    
    return user


@pytest.fixture
def auth_client(client, admin_user):
    """
    Create authenticated test client with admin user.
    """
    with client.session_transaction() as sess:
        sess['_user_id'] = admin_user.id
        sess['_fresh'] = True
    
    return client


@pytest.fixture
def sample_cve(db):
    """Create sample CVE for testing."""
    from app.models.nvd import CVE
    
    cve = CVE(
        cve_id='CVE-2024-0001',
        source_identifier='nvd@nist.gov',
        published=datetime(2024, 1, 1, tzinfo=timezone.utc),
        last_modified=datetime(2024, 1, 15, tzinfo=timezone.utc),
        vuln_status='Analyzed',
        descriptions=[{
            'lang': 'en',
            'value': 'Test vulnerability description'
        }],
        cvss_v31_score=9.8,
        cvss_v31_vector='CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
        cvss_v31_severity='CRITICAL',
        vendors=['testvendor'],
        products=['testproduct'],
        weaknesses=['CWE-79'],
        references=[{
            'url': 'https://example.com/advisory',
            'source': 'cve@mitre.org'
        }],
        cisa_kev=False,
    )
    
    db.session.add(cve)
    db.session.commit()
    
    return cve


@pytest.fixture
def sample_cves(db):
    """Create multiple sample CVEs for testing."""
    from app.models.nvd import CVE
    
    cves = []
    
    severities = [
        ('CRITICAL', 9.8),
        ('HIGH', 8.5),
        ('MEDIUM', 5.5),
        ('LOW', 3.2),
    ]
    
    for i, (severity, score) in enumerate(severities):
        cve = CVE(
            cve_id=f'CVE-2024-{str(i+1).zfill(4)}',
            source_identifier='nvd@nist.gov',
            published=datetime(2024, 1, i+1, tzinfo=timezone.utc),
            last_modified=datetime(2024, 1, i+15, tzinfo=timezone.utc),
            vuln_status='Analyzed',
            descriptions=[{
                'lang': 'en',
                'value': f'Test vulnerability {i+1} description'
            }],
            cvss_v31_score=score,
            cvss_v31_severity=severity,
            vendors=[f'vendor{i+1}'],
            products=[f'product{i+1}'],
            weaknesses=[f'CWE-{i+1}'],
        )
        cves.append(cve)
        db.session.add(cve)
    
    db.session.commit()
    
    return cves


@pytest.fixture
def sample_asset(db, admin_user):
    """Create sample asset for testing."""
    from app.models.inventory import Asset
    from app.models.system.enums import AssetType, AssetStatus
    
    asset = Asset(
        name='Test Server',
        asset_type=AssetType.SERVER,
        ip_address='192.168.1.100',
        hostname='test-server.local',
        operating_system='Ubuntu 22.04 LTS',
        criticality=5,
        status=AssetStatus.ACTIVE,
        owner_id=admin_user.id,
        description='Test server for unit tests',
        software=[
            {'name': 'nginx', 'version': '1.24.0'},
            {'name': 'postgresql', 'version': '15.0'},
        ],
    )
    
    db.session.add(asset)
    db.session.commit()
    
    return asset


@pytest.fixture
def sample_monitoring_rule(db, admin_user):
    """Create sample monitoring rule for testing."""
    from app.models.monitoring import MonitoringRule
    from app.models.system.enums import MonitoringRuleType, AlertChannel, Severity
    
    rule = MonitoringRule(
        name='Test Rule',
        description='Test monitoring rule',
        rule_type=MonitoringRuleType.SEVERITY_THRESHOLD,
        is_active=True,
        severity_threshold=Severity.HIGH,
        alert_channel=AlertChannel.EMAIL,
        alert_config={'recipients': ['test@example.com']},
        created_by_id=admin_user.id,
    )
    
    db.session.add(rule)
    db.session.commit()
    
    return rule


@pytest.fixture
def api_headers(admin_user):
    """Create headers with API key for testing."""
    return {
        'X-API-Key': admin_user.api_key or 'test-api-key',
        'Content-Type': 'application/json',
    }


# =============================================================================
# Helper Functions
# =============================================================================

def login_user(client, username: str, password: str) -> bool:
    """
    Helper to login user via test client.
    
    Args:
        client: Test client
        username: Username
        password: Password
        
    Returns:
        True if login successful
    """
    response = client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)
    
    return response.status_code == 200


def logout_user(client) -> bool:
    """
    Helper to logout user via test client.
    
    Args:
        client: Test client
        
    Returns:
        True if logout successful
    """
    response = client.get('/auth/logout', follow_redirects=True)
    return response.status_code == 200


def get_json(client, url: str, **kwargs) -> Dict[str, Any]:
    """
    Helper to GET JSON from API.
    
    Args:
        client: Test client
        url: API URL
        **kwargs: Additional request arguments
        
    Returns:
        JSON response data
    """
    response = client.get(url, **kwargs)
    return response.get_json() if response.content_type == 'application/json' else {}


def post_json(client, url: str, data: Dict, **kwargs) -> Dict[str, Any]:
    """
    Helper to POST JSON to API.
    
    Args:
        client: Test client
        url: API URL
        data: Request body
        **kwargs: Additional request arguments
        
    Returns:
        JSON response data
    """
    response = client.post(
        url,
        json=data,
        content_type='application/json',
        **kwargs
    )
    return response.get_json() if response.content_type == 'application/json' else {}
