# app/forms/profile_form.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, PasswordField, SubmitField
from wtforms.validators import (
    DataRequired, Length, Email, Optional, EqualTo, Regexp
)
from wtforms.widgets import TextArea


class ProfileForm(FlaskForm):
    """Form for editing user profile."""

    first_name = StringField(
        'First Name',
        validators=[
            DataRequired(message="First name is required."),
            Length(2, 50, message="First name must be between 2 and 50 characters."),
            Regexp(
                r'^[A-Za-z\u00C0-\u00FF\s]+$',
                message="First name must contain only letters and spaces."
            )
        ],
        render_kw={
            'placeholder': 'Enter your first name',
            'class': 'form-control'
        }
    )

    last_name = StringField(
        'Last Name',
        validators=[
            DataRequired(message="Last name is required."),
            Length(2, 50, message="Last name must be between 2 and 50 characters."),
            Regexp(
                r'^[A-Za-z\u00C0-\u00FF\s]+$',
                message="Last name must contain only letters and spaces."
            )
        ],
        render_kw={
            'placeholder': 'Enter your last name',
            'class': 'form-control'
        }
    )

    email = StringField(
        'Email',
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Invalid email format."),
            Length(max=255, message="Email is too long.")
        ],
        render_kw={
            'placeholder': 'example@domain.com',
            'class': 'form-control',
            'autocomplete': 'email'
        }
    )

    phone = StringField(
        'Phone',
        validators=[
            Optional(),
            Length(max=20, message="Phone is too long."),
            Regexp(
                r'^[\+]?[1-9]?[0-9]{7,15}$',
                message="Invalid phone format."
            )
        ],
        render_kw={
            'placeholder': '+55 (11) 99999-9999',
            'class': 'form-control'
        }
    )

    address = TextAreaField(
        'Address',
        validators=[
            Optional(),
            Length(max=500, message="Address is too long.")
        ],
        widget=TextArea(),
        render_kw={
            'placeholder': 'Enter your full address',
            'class': 'form-control',
            'rows': 3
        }
    )

    bio = TextAreaField(
        'Biography',
        validators=[
            Optional(),
            Length(max=1000, message="Biography is too long.")
        ],
        widget=TextArea(),
        render_kw={
            'placeholder': 'Tell us a little about yourself...',
            'class': 'form-control',
            'rows': 4
        }
    )

    profile_picture = FileField(
        'Profile Picture',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Only images are allowed!')
        ]
    )

    submit = SubmitField(
        'Save Changes',
        render_kw={'class': 'btn btn-primary'}
    )


class ChangePasswordForm(FlaskForm):
    """Form for changing password."""

    current_password = PasswordField(
        'Current Password',
        validators=[
            DataRequired(message="Current password is required.")
        ],
        render_kw={
            'placeholder': 'Enter your current password',
            'class': 'form-control'
        }
    )

    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message="New password is required."),
            Length(8, 128, message="Password must be at least 8 characters long."),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
                message="Password must contain at least: 1 lowercase letter, 1 uppercase letter, 1 number, and 1 special character."
            )
        ],
        render_kw={
            'placeholder': 'Enter your new password',
            'class': 'form-control'
        }
    )

    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(message="Precisa confirmar a nova senha."),
            EqualTo('new_password', message="As senhas devem coincidir.")
        ],
        render_kw={
            'placeholder': 'Confirme sua nova senha',
            'class': 'form-control'
        }
    )

    submit = SubmitField(
        'Alterar Senha',
        render_kw={'class': 'btn btn-primary'}
    )


class DeleteAccountForm(FlaskForm):
    """Formulario para exclusao de conta."""

    password = PasswordField(
        'Senha',
        validators=[
            DataRequired(message="A senha e obrigatoria para excluir a conta.")
        ],
        render_kw={
            'placeholder': 'Digite sua senha para confirmar',
            'class': 'form-control'
        }
    )

    confirmation = StringField(
        'Confirmacao',
        validators=[
            DataRequired(message="Digite 'EXCLUIR' para confirmar."),
            EqualTo('confirmation', message="Digite exatamente 'EXCLUIR' para confirmar.")
        ],
        render_kw={
            'placeholder': 'Digite EXCLUIR para confirmar',
            'class': 'form-control'
        }
    )

    submit = SubmitField(
        'Excluir Conta',
        render_kw={'class': 'btn btn-danger'}
    )
