# app/forms/asset_form.py

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

class AssetForm(FlaskForm):
    """
    Formulario para criar/editar um Asset.
    - name: nome amigavel do ativo
    - ip_address: endereco IPv4 do ativo
    """

    name = StringField(
        'Nome',
        validators=[
            DataRequired(message="O nome e obrigatorio."),
            Length(max=100, message="Maximo 100 caracteres.")
        ]
    )

    ip_address = StringField(
        'Endereco IP',
        validators=[
            DataRequired(message="O endereco IP e obrigatorio."),
            Regexp(
                r'^(\d{1,3}\.){3}\d{1,3}$',
                message="Informe um IPv4 valido (ex: 192.168.0.1)."
            )
        ]
    )

    submit = SubmitField('Salvar')
