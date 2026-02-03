"""
Open-Monitor Auth Forms
Formulários de autenticação usando Flask-WTF.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, 
    ValidationError, Regexp
)


class LoginForm(FlaskForm):
    """Formulário de login."""
    username = StringField(
        'Usuário',
        validators=[
            DataRequired(message='Usuário é obrigatório'),
            Length(min=3, max=64, message='Usuário deve ter entre 3 e 64 caracteres')
        ],
        render_kw={'placeholder': 'Digite seu usuário', 'autocomplete': 'username'}
    )
    
    password = PasswordField(
        'Senha',
        validators=[
            DataRequired(message='Senha é obrigatória')
        ],
        render_kw={'placeholder': 'Digite sua senha', 'autocomplete': 'current-password'}
    )
    
    remember_me = BooleanField('Manter conectado')
    
    submit = SubmitField('Entrar')


class RegisterForm(FlaskForm):
    """Formulário de registro de novos usuários."""
    username = StringField(
        'Usuário',
        validators=[
            DataRequired(message='Usuário é obrigatório'),
            Length(min=3, max=64, message='Usuário deve ter entre 3 e 64 caracteres'),
            Regexp(
                r'^[a-zA-Z0-9_]+$',
                message='Usuário pode conter apenas letras, números e underscore'
            )
        ],
        render_kw={'placeholder': 'Escolha um nome de usuário', 'autocomplete': 'username'}
    )
    
    email = StringField(
        'E-mail',
        validators=[
            DataRequired(message='E-mail é obrigatório'),
            Email(message='E-mail inválido'),
            Length(max=255, message='E-mail muito longo')
        ],
        render_kw={'placeholder': 'seu@email.com', 'autocomplete': 'email'}
    )
    
    password = PasswordField(
        'Senha',
        validators=[
            DataRequired(message='Senha é obrigatória'),
            Length(min=12, message='Senha deve ter no mínimo 12 caracteres')
        ],
        render_kw={'placeholder': 'Mínimo 12 caracteres', 'autocomplete': 'new-password'}
    )
    
    confirm_password = PasswordField(
        'Confirmar Senha',
        validators=[
            DataRequired(message='Confirmação de senha é obrigatória'),
            EqualTo('password', message='As senhas devem ser iguais')
        ],
        render_kw={'placeholder': 'Repita a senha', 'autocomplete': 'new-password'}
    )
    
    accept_terms = BooleanField(
        'Li e aceito os Termos de Uso',
        validators=[
            DataRequired(message='Você deve aceitar os termos para continuar')
        ]
    )
    
    submit = SubmitField('Criar Conta')


class InitRootForm(FlaskForm):
    """Formulário para criar primeiro usuário admin (init-root)."""
    username = StringField(
        'Usuário Admin',
        validators=[
            DataRequired(message='Usuário é obrigatório'),
            Length(min=3, max=64, message='Usuário deve ter entre 3 e 64 caracteres'),
            Regexp(
                r'^[a-zA-Z0-9_]+$',
                message='Usuário pode conter apenas letras, números e underscore'
            )
        ],
        render_kw={'placeholder': 'admin', 'autocomplete': 'username'}
    )
    
    email = StringField(
        'E-mail',
        validators=[
            DataRequired(message='E-mail é obrigatório'),
            Email(message='E-mail inválido'),
            Length(max=255, message='E-mail muito longo')
        ],
        render_kw={'placeholder': 'admin@empresa.com', 'autocomplete': 'email'}
    )
    
    password = PasswordField(
        'Senha',
        validators=[
            DataRequired(message='Senha é obrigatória'),
            Length(min=12, message='Senha deve ter no mínimo 12 caracteres')
        ],
        render_kw={'placeholder': 'Mínimo 12 caracteres', 'autocomplete': 'new-password'}
    )
    
    confirm_password = PasswordField(
        'Confirmar Senha',
        validators=[
            DataRequired(message='Confirmação de senha é obrigatória'),
            EqualTo('password', message='As senhas devem ser iguais')
        ],
        render_kw={'placeholder': 'Repita a senha', 'autocomplete': 'new-password'}
    )
    
    nvd_api_key = StringField(
        'NVD API Key',
        validators=[
            Length(max=255, message='API Key muito longa')
        ],
        render_kw={'placeholder': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'}
    )
    
    start_sync = BooleanField(
        'Iniciar Sincronização',
        default=True
    )
    
    organization_name = StringField(
        'Nome da Organização',
        validators=[
            Length(max=128, message='Nome muito longo')
        ],
        render_kw={'placeholder': 'Minha Empresa (opcional)'}
    )
    
    submit = SubmitField('Inicializar Sistema')


class PasswordResetRequestForm(FlaskForm):
    """Formulário para solicitar reset de senha."""
    email = StringField(
        'E-mail',
        validators=[
            DataRequired(message='E-mail é obrigatório'),
            Email(message='E-mail inválido')
        ],
        render_kw={'placeholder': 'Digite seu e-mail cadastrado', 'autocomplete': 'email'}
    )
    
    submit = SubmitField('Enviar Link de Reset')


class PasswordResetForm(FlaskForm):
    """Formulário para redefinir senha."""
    password = PasswordField(
        'Nova Senha',
        validators=[
            DataRequired(message='Senha é obrigatória'),
            Length(min=12, message='Senha deve ter no mínimo 12 caracteres')
        ],
        render_kw={'placeholder': 'Mínimo 12 caracteres', 'autocomplete': 'new-password'}
    )
    
    confirm_password = PasswordField(
        'Confirmar Nova Senha',
        validators=[
            DataRequired(message='Confirmação de senha é obrigatória'),
            EqualTo('password', message='As senhas devem ser iguais')
        ],
        render_kw={'placeholder': 'Repita a nova senha', 'autocomplete': 'new-password'}
    )
    
    submit = SubmitField('Redefinir Senha')


class ChangePasswordForm(FlaskForm):
    """Formulário para alterar senha (usuário logado)."""
    current_password = PasswordField(
        'Senha Atual',
        validators=[
            DataRequired(message='Senha atual é obrigatória')
        ],
        render_kw={'placeholder': 'Digite sua senha atual', 'autocomplete': 'current-password'}
    )
    
    new_password = PasswordField(
        'Nova Senha',
        validators=[
            DataRequired(message='Nova senha é obrigatória'),
            Length(min=12, message='Senha deve ter no mínimo 12 caracteres')
        ],
        render_kw={'placeholder': 'Mínimo 12 caracteres', 'autocomplete': 'new-password'}
    )
    
    confirm_new_password = PasswordField(
        'Confirmar Nova Senha',
        validators=[
            DataRequired(message='Confirmação de senha é obrigatória'),
            EqualTo('new_password', message='As senhas devem ser iguais')
        ],
        render_kw={'placeholder': 'Repita a nova senha', 'autocomplete': 'new-password'}
    )
    
    submit = SubmitField('Alterar Senha')


class ProfileForm(FlaskForm):
    """Formulário para editar perfil do usuário."""
    username = StringField(
        'Usuário',
        validators=[
            DataRequired(message='Usuário é obrigatório'),
            Length(min=3, max=64, message='Usuário deve ter entre 3 e 64 caracteres'),
            Regexp(
                r'^[a-zA-Z0-9_]+$',
                message='Usuário pode conter apenas letras, números e underscore'
            )
        ],
        render_kw={'placeholder': 'Seu nome de usuário', 'autocomplete': 'username'}
    )
    
    email = StringField(
        'E-mail',
        validators=[
            DataRequired(message='E-mail é obrigatório'),
            Email(message='E-mail inválido'),
            Length(max=255, message='E-mail muito longo')
        ],
        render_kw={'placeholder': 'seu@email.com', 'autocomplete': 'email'}
    )
    
    submit = SubmitField('Salvar Alterações')


class ApiKeyForm(FlaskForm):
    """Formulário para gerenciar API Key."""
    submit = SubmitField('Gerar Nova API Key')
    revoke = SubmitField('Revogar API Key')