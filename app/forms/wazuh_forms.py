"""Flask-WTF forms for the Wazuh integration (admin-only config)."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField, IntegerField,
)
from wtforms.validators import (
    DataRequired, Length, NumberRange, Optional as WTOptional, ValidationError,
    Regexp,
)


class WazuhConfigForm(FlaskForm):
    """Configuração da integração com o Wazuh Indexer."""

    enabled = BooleanField('Habilitar integração Wazuh')

    url = StringField(
        'URL do Wazuh Indexer',
        validators=[
            Length(max=500, message='URL muito longa'),
            Regexp(r'^(https?://.+)?$', message='URL deve começar com http:// ou https://'),
        ],
        render_kw={'placeholder': 'https://wazuh-indexer:9200', 'autocomplete': 'off'},
    )

    username = StringField(
        'Usuário',
        validators=[Length(max=128)],
        render_kw={'placeholder': 'admin', 'autocomplete': 'off'},
    )

    password = PasswordField(
        'Senha',
        validators=[WTOptional(), Length(max=255)],
        render_kw={
            'placeholder': 'Deixe em branco para manter a atual',
            'autocomplete': 'new-password',
        },
    )

    verify_tls = BooleanField(
        'Verificar certificado TLS',
        default=True,
    )

    index_pattern = StringField(
        'Padrão de índice',
        validators=[WTOptional(), Length(max=255)],
        default='wazuh-alerts-*',
        render_kw={'placeholder': 'wazuh-alerts-*'},
    )

    min_rule_level = IntegerField(
        'Nível mínimo de regra (rule.level 0-15)',
        default=0,
        validators=[
            WTOptional(),
            NumberRange(min=0, max=15, message='rule.level deve estar entre 0 e 15'),
        ],
    )

    poll_interval_seconds = IntegerField(
        'Intervalo de polling (segundos)',
        default=60,
        validators=[
            WTOptional(),
            NumberRange(min=10, max=3600, message='Polling entre 10 e 3600 segundos'),
        ],
    )

    submit_save = SubmitField('Salvar configuração')
    submit_test = SubmitField('Testar conexão')
    submit_sync = SubmitField('Sincronizar agora')

    def validate_url(self, field):
        # Required only when enabled
        if self.enabled.data and not (field.data or '').strip():
            raise ValidationError('URL é obrigatória quando a integração está habilitada.')

    def validate_username(self, field):
        if self.enabled.data and not (field.data or '').strip():
            raise ValidationError('Usuário é obrigatório quando a integração está habilitada.')
