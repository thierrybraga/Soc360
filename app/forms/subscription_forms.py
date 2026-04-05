# app/forms/subscription_forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional
from wtforms.widgets import TextArea


class NewsletterSubscriptionForm(FlaskForm):
    """Form for newsletter subscription."""

    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.'),
            Length(max=255, message='Email address must be less than 255 characters.')
        ],
        render_kw={
            'placeholder': 'your.email@example.com',
            'class': 'form-control',
            'autocomplete': 'email'
        }
    )

    email_notifications = BooleanField(
        'Email Notifications',
        default=True,
        render_kw={'class': 'form-check-input'}
    )

    preferences = TextAreaField(
        'Notification Preferences',
        validators=[Optional(), Length(max=1000)],
        render_kw={
            'placeholder': 'Optional: Specify your notification preferences...',
            'class': 'form-control',
            'rows': 3
        }
    )

    source = SelectField(
        'How did you hear about us?',
        choices=[
            ('website', 'Website'),
            ('social_media', 'Social Media'),
            ('referral', 'Referral'),
            ('search_engine', 'Search Engine'),
            ('other', 'Other')
        ],
        default='website',
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )


class NewsletterUnsubscribeForm(FlaskForm):
    """Form for newsletter unsubscription."""

    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.')
        ],
        render_kw={
            'placeholder': 'your.email@example.com',
            'class': 'form-control',
            'autocomplete': 'email'
        }
    )


# Alias for backward compatibility
NewsletterForm = NewsletterSubscriptionForm