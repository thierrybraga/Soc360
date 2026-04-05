# app/forms/common_form.py

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, SelectField, DateField
from wtforms.validators import Optional, NumberRange, DataRequired, Email

class SearchForm(FlaskForm):
    q = StringField('Search', validators=[Optional()])
    submit = SubmitField('Search')

class PaginationForm(FlaskForm):
    page = IntegerField('Page', default=1, validators=[NumberRange(min=1, message='Page must be >= 1')])
    per_page = IntegerField('Per page', default=20, validators=[NumberRange(min=1, max=100, message='Items per page between 1 and 100')])
    submit = SubmitField('Go')

class FilterForm(FlaskForm):
    severity = SelectField(
        'Severity',
        choices=[('', 'All'), ('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')],
        validators=[Optional()]
    )
    vendor = StringField('Vendor', validators=[Optional()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Filter')

class DeleteForm(FlaskForm):
    """Simple form for deletion confirmation."""
    submit = SubmitField('Delete')
