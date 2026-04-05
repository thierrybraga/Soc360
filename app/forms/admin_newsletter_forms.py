# app/forms/admin_newsletter_forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length
from wtforms.widgets import TextArea


class NewsletterAdminForm(FlaskForm):
    """Admin form for managing newsletter subscriptions."""

    subject = StringField(
        'Email Subject',
        validators=[
            DataRequired(message='Subject is required.'),
            Length(max=200, message='Subject must be less than 200 characters.')
        ],
        render_kw={
            'placeholder': 'Newsletter subject...',
            'class': 'form-control'
        }
    )

    content = TextAreaField(
        'Email Content',
        validators=[
            DataRequired(message='Content is required.'),
            Length(max=10000, message='Content must be less than 10,000 characters.')
        ],
        widget=TextArea(),
        render_kw={
            'placeholder': 'Newsletter content in HTML or plain text...',
            'class': 'form-control',
            'rows': 15
        }
    )

    content_type = SelectField(
        'Content Type',
        choices=[
            ('html', 'HTML'),
            ('plain', 'Plain Text')
        ],
        default='html',
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )

    send_to_active_only = BooleanField(
        'Send to active subscribers only',
        default=True,
        render_kw={'class': 'form-check-input'}
    )