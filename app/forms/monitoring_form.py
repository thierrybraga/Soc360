# app/forms/monitoring_form.py

import json
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError

class MonitoringRuleForm(FlaskForm):
    """
    Formulario para criar/editar uma regra de monitoramento.
    Campos:
      - name: nome descritivo da regra
      - parameters: configuracao da regra em JSON
    """
    name = StringField(
        'Nome da Regra',
        validators=[
            DataRequired(message="O nome da regra e obrigatorio."),
            Length(max=100, message="Maximo 100 caracteres.")
        ]
    )
    parameters = TextAreaField(
        'Parametros (JSON)',
        validators=[DataRequired(message="Parametros sao obrigatorios.")]
    )
    submit = SubmitField('Salvar')

    def validate_parameters(self, field):
        """Valida que o conteudo de parameters seja um JSON valido."""
        try:
            json.loads(field.data or '')
        except ValueError:
            raise ValidationError('Parametros devem ser um JSON valido.')
