import pytest


@pytest.mark.usefixtures('admin_user')
def test_admin_failed_login_increments_counter_without_500(client, admin_user, db):
    response = client.post(
        '/auth/login',
        data={
            'username': admin_user.username,
            'password': 'senha-incorreta'
        },
        follow_redirects=True
    )

    db.session.refresh(admin_user)

    assert response.status_code == 200
    assert b'Invalid username or password.' in response.data
    assert admin_user.failed_login_count == 1


def test_admin_successful_login_resets_failed_counter(client, admin_user, db):
    admin_user.failed_login_count = 3
    db.session.commit()

    response = client.post(
        '/auth/login',
        data={
            'username': admin_user.username,
            'password': 'Admin123!@#Test'
        },
        follow_redirects=False
    )

    db.session.refresh(admin_user)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')
    assert admin_user.failed_login_count == 0
