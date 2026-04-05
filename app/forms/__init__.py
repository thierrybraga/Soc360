"""
Open-Monitor Forms Package
Flask-WTF form classes.
"""

from .auth_forms import LoginForm, RegisterForm

try:
    from .asset_form import AssetForm
except ImportError:
    AssetForm = None

try:
    from .vulnerability_form import VulnerabilityForm
except ImportError:
    VulnerabilityForm = None

try:
    from .report_form import ReportFilterForm
except ImportError:
    ReportFilterForm = None

try:
    from .api_form import APIQueryForm
except ImportError:
    APIQueryForm = None

try:
    from .common_form import SearchForm, PaginationForm, FilterForm, DeleteForm
except ImportError:
    SearchForm = None
    PaginationForm = None
    FilterForm = None
    DeleteForm = None

try:
    from .monitoring_form import MonitoringRuleForm
except ImportError:
    MonitoringRuleForm = None

try:
    from .subscription_forms import NewsletterSubscriptionForm, NewsletterUnsubscribeForm, NewsletterForm
except ImportError:
    NewsletterSubscriptionForm = None
    NewsletterUnsubscribeForm = None
    NewsletterForm = None

try:
    from .admin_newsletter_forms import NewsletterAdminForm
except ImportError:
    NewsletterAdminForm = None

try:
    from .profile_form import ProfileForm, ChangePasswordForm
except ImportError:
    ProfileForm = None
    ChangePasswordForm = None

__all__ = [
    'LoginForm', 'RegisterForm',
    'AssetForm', 'VulnerabilityForm', 'ReportFilterForm', 'APIQueryForm',
    'SearchForm', 'NewsletterForm', 'PaginationForm', 'FilterForm', 'DeleteForm',
    'MonitoringRuleForm',
    'NewsletterSubscriptionForm', 'NewsletterUnsubscribeForm', 'NewsletterAdminForm',
    'ProfileForm', 'ChangePasswordForm',
]
