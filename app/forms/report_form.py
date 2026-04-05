# app/forms/report_form.py

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField
from wtforms.validators import Optional, ValidationError
from app.models.system.enums import Severity

class ReportFilterForm(FlaskForm):
    """
    Formulario para filtrar e gerar relatorios.
    Campos:
      - start_date: data inicial do periodo
      - end_date:   data final do periodo
      - severity:   nivel de severidade (LOW, MEDIUM, HIGH, CRITICAL)
      - vendor:     nome do fornecedor para filtrar
    """

    start_date = DateField(
        'Data Inicial',
        format='%Y-%m-%d',
        validators=[Optional()],
        render_kw={"placeholder": "YYYY-MM-DD"}
    )
    end_date = DateField(
        'Data Final',
        format='%Y-%m-%d',
        validators=[Optional()],
        render_kw={"placeholder": "YYYY-MM-DD"}
    )
    severity = SelectField(
        'Severidade',
        choices=[('', 'Todas')] + [(s.value, s.value) for s in Severity if s != Severity.NONE],
        validators=[Optional()]
    )
    vendor = StringField(
        'Fornecedor',
        validators=[Optional()],
        render_kw={"placeholder": "ex: Microsoft"}
    )
    submit = SubmitField('Gerar Relatorio')

    def validate_end_date(self, field):
        if self.start_date.data and field.data:
            if field.data < self.start_date.data:
                raise ValidationError('Data Final deve ser igual ou posterior a Data Inicial.')
