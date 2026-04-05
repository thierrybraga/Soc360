from app.models.monitoring import Alert, MonitoringRule
from app.models.system.enums import AlertStatus, MonitoringRuleType, Severity


def authenticate_client(client, user):
    response = client.post(
        '/auth/login',
        data={
            'username': user.username,
            'password': 'Admin123!@#Test'
        },
        follow_redirects=False
    )

    assert response.status_code == 302
    return client


def create_alert_for_user(db, user, suffix='principal', status=AlertStatus.NEW.value):
    rule = MonitoringRule(
        name=f'Regra {suffix}',
        user_id=user.id,
        rule_type=MonitoringRuleType.NEW_CVE.value,
        enabled=True,
        parameters={},
        alert_channels=[]
    )
    db.session.add(rule)
    db.session.flush()

    alert = Alert(
        title=f'Alerta {suffix}',
        description='Descrição de teste',
        rule_id=rule.id,
        status=status,
        severity=Severity.HIGH.value,
        details={'source': 'test'}
    )
    db.session.add(alert)
    db.session.commit()
    return alert, rule


def test_alerts_page_renders_modal(client, admin_user):
    authenticate_client(client, admin_user)
    response = client.get('/monitoring/alerts')

    assert response.status_code == 200
    assert b'alertDetailsModal' in response.data
    assert b'alerts-table-body' in response.data


def test_alerts_api_returns_pagination_metadata(client, admin_user, db):
    authenticate_client(client, admin_user)
    create_alert_for_user(db, admin_user, 'um')
    create_alert_for_user(db, admin_user, 'dois')

    response = client.get('/monitoring/api/alerts?per_page=1&page=1')
    data = response.get_json()

    assert response.status_code == 200
    assert data['total'] == 2
    assert data['pages'] == 2
    assert data['per_page'] == 1
    assert data['has_prev'] is False
    assert data['has_next'] is True
    assert data['next_num'] == 2
    assert len(data['items']) == 1


def test_update_alert_status_marks_alert_as_acknowledged(client, admin_user, db):
    authenticate_client(client, admin_user)
    alert, _rule = create_alert_for_user(db, admin_user)

    response = client.put(
        f'/monitoring/api/alerts/{alert.id}/status',
        json={'status': AlertStatus.ACKNOWLEDGED.value}
    )

    db.session.refresh(alert)
    data = response.get_json()

    assert response.status_code == 200
    assert data['status'] == AlertStatus.ACKNOWLEDGED.value
    assert alert.status == AlertStatus.ACKNOWLEDGED.value
    assert alert.acknowledged_by_id == admin_user.id
    assert alert.acknowledged_at is not None
