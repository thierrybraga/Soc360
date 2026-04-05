# app/forms/api_form.py

"""
Formulario para validar parametros de query em endpoints de API
(cves, vulnerabilities, assets) usando Flask-WTF para CSRF e validacao de tipos.
"""

from flask_wtf import FlaskForm
from wtforms import Form, StringField, IntegerField, SelectField, SubmitField
from wtforms.validators import Optional, NumberRange

from app.models.system.enums import Severity

class APIQueryForm(FlaskForm):
    """
    Valida parametros de paginacao e filtros comuns para API endpoints:
      - page: numero da pagina (>= 1)
      - per_page: itens por pagina (entre 1 e 100)
      - severity: nivel de severidade (LOW, MEDIUM, HIGH, CRITICAL)
      - vendor: nome do fornecedor (string)
    """
    page = IntegerField(
        label='Pagina',
        default=1,
        validators=[
            Optional(),
            NumberRange(min=1, message="Pagina deve ser maior ou igual a 1")
        ]
    )
    per_page = IntegerField(
        label='Itens por pagina',
        default=20,
        validators=[
            Optional(),
            NumberRange(min=1, max=100, message="Itens por pagina deve ser entre 1 e 100")
        ]
    )
    severity = SelectField(
        label='Severidade',
        choices=[('', 'Todas')] + [(s.value, s.value) for s in Severity if s != Severity.NONE],
        validators=[Optional()]
    )
    vendor = StringField(
        label='Fornecedor',
        validators=[Optional()]
    )
    submit = SubmitField('Aplicar')
