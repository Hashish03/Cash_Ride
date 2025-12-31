from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator, EmailValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid


class UserManager(BaseUserManager):
    """Custom user manager with support for social login"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        email = self.normalize_email(email)
        
        # Generate username if not provided
        if 'username' not in extra_fields:
            username = email.split('@')[0]
            # Ensure username is unique
            counter = 1
            while self.model.objects.filter(username=username).exists():
                username = f"{email.split('@')[0]}_{counter}"
                counter += 1
            extra_fields['username'] = username
        
        user = self.model(email=email, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)
    
    def get_or_create_by_social(self, provider, social_uid, email=None, **extra_fields):
        """Get or create user by social provider and UID"""
        try:
            # Try to find by social_uid first
            user = self.get(
                social_provider=provider,
                social_uid=social_uid
            )
            created = False
        except self.model.DoesNotExist:
            try:
                # Try to find by email if provided
                if email:
                    user = self.get(email=email)
                    # Update with social info
                    user.social_provider = provider
                    user.social_uid = social_uid
                    user.save()
                    created = False
                else:
                    # Create new user
                    user = self.create_user(
                        email=email or f"{provider}_{social_uid}@{provider}.com",
                        **extra_fields
                    )
                    user.social_provider = provider
                    user.social_uid = social_uid
                    if not email:
                        user.email_verified = True  # Social logins are verified
                    user.save()
                    created = True
            except self.model.DoesNotExist:
                # Create new user
                user = self.create_user(
                    email=email or f"{provider}_{social_uid}@{provider}.com",
                    **extra_fields
                )
                user.social_provider = provider
                user.social_uid = social_uid
                if not email:
                    user.email_verified = True  # Social logins are verified
                user.save()
                created = True
        
        return user, created


class User(AbstractUser):
    """Extended user model with Supabase and social login support"""
    
    # Auth fields
    email = models.EmailField(
        _('email address'),
        unique=True,
        validators=[EmailValidator()],
        error_messages={
            'unique': _("A user with that email already exists."),
        }
    )
    
    # Supabase integration
    supabase_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('Supabase User ID')
    )
    
    # Phone number
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_('Phone Number')
    )
    
    # Verification
    email_verified = models.BooleanField(
        default=False,
        verbose_name=_('Email Verified')
    )
    phone_verified = models.BooleanField(
        default=False,
        verbose_name=_('Phone Verified')
    )
    verification_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Verification Token')
    )
    verification_token_expires = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Verification Token Expires')
    )
    
    # Profile
    profile_picture = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Profile Picture URL')
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Date of Birth')
    )
    
    # Social login
    SOCIAL_PROVIDERS = (
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('apple', 'Apple'),
        ('github', 'GitHub'),
        ('twitter', 'Twitter'),
        ('linkedin', 'LinkedIn'),
        ('microsoft', 'Microsoft'),
    )
    
    social_provider = models.CharField(
        max_length=50,
        choices=SOCIAL_PROVIDERS,
        blank=True,
        null=True,
        verbose_name=_('Social Provider')
    )
    social_uid = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Social User ID')
    )
    social_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Social Data')
    )
    
    # Security
    two_factor_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Two-Factor Authentication Enabled')
    )
    two_factor_secret = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Two-Factor Secret')
    )
    last_login_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_('Last Login IP')
    )
    
    # Account status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    account_locked_until = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Account Locked Until')
    )
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Failed Login Attempts')
    )
    last_failed_login = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Last Failed Login')
    )
    
    # Preferences
    preferred_language = models.CharField(
        max_length=10,
        default='en',
        verbose_name=_('Preferred Language')
    )
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        verbose_name=_('Timezone')
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        verbose_name=_('Currency')
    )
    
    # Terms and consent
    terms_accepted = models.BooleanField(
        default=False,
        verbose_name=_('Terms Accepted')
    )
    terms_accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Terms Accepted At')
    )
    privacy_policy_accepted = models.BooleanField(
        default=False,
        verbose_name=_('Privacy Policy Accepted')
    )
    privacy_policy_accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Privacy Policy Accepted At')
    )
    marketing_opt_in = models.BooleanField(
        default=False,
        verbose_name=_('Marketing Opt-in')
    )
    email_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Email Notifications')
    )
    push_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Push Notifications')
    )
    sms_notifications = models.BooleanField(
        default=False,
        verbose_name=_('SMS Notifications')
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    last_profile_update = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Last Profile Update')
    )
    
    # Set email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['supabase_id']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['social_provider', 'social_uid']),
            models.Index(fields=['email_verified', 'phone_verified']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.email
    
    def clean(self):
        """Custom validation"""
        super().clean()
        
        if self.social_provider and not self.social_uid:
            raise ValidationError({
                'social_uid': _('Social UID is required when social provider is specified.')
            })
        
        if self.social_uid and not self.social_provider:
            raise ValidationError({
                'social_provider': _('Social provider is required when social UID is specified.')
            })
        
        # Ensure email is verified for social logins
        if self.social_provider and not self.email_verified:
            self.email_verified = True
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        """Return the full name of the user"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split('@')[0]
    
    @property
    def is_social_user(self):
        """Check if user signed up via social login"""
        return bool(self.social_provider and self.social_uid)
    
    @property
    def is_account_locked(self):
        """Check if account is currently locked"""
        if not self.account_locked_until:
            return False
        return timezone.now() < self.account_locked_until
    
    @property
    def has_password(self):
        """Check if user has a password set"""
        return self.has_usable_password()
    
    def get_display_name(self):
        """Get display name for UI"""
        if self.first_name:
            return self.first_name
        return self.email.split('@')[0]
    
    def unlock_account(self):
        """Unlock the user account"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts', 'updated_at'])
    
    def record_successful_login(self, ip_address=None):
        """Record successful login"""
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None
        self.save(update_fields=[
            'last_login_ip', 'failed_login_attempts', 'last_failed_login',
            'account_locked_until', 'updated_at'
        ])
    
    def record_failed_login(self):
        """Record failed login attempt"""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)
        
        self.save(update_fields=[
            'failed_login_attempts', 'last_failed_login',
            'account_locked_until', 'updated_at'
        ])
    
    def accept_terms(self):
        """Accept terms and conditions"""
        self.terms_accepted = True
        self.terms_accepted_at = timezone.now()
        self.save(update_fields=['terms_accepted', 'terms_accepted_at', 'updated_at'])
    
    def accept_privacy_policy(self):
        """Accept privacy policy"""
        self.privacy_policy_accepted = True
        self.privacy_policy_accepted_at = timezone.now()
        self.save(update_fields=['privacy_policy_accepted', 'privacy_policy_accepted_at', 'updated_at'])
    
    def update_profile_picture(self, url):
        """Update profile picture"""
        self.profile_picture = url
        self.last_profile_update = timezone.now()
        self.save(update_fields=['profile_picture', 'last_profile_update', 'updated_at'])
    
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'display_name': self.get_display_name(),
            'phone_number': self.phone_number,
            'profile_picture': self.profile_picture,
            'email_verified': self.email_verified,
            'phone_verified': self.phone_verified,
            'social_provider': self.social_provider,
            'is_social_user': self.is_social_user,
            'has_password': self.has_password,
            'two_factor_enabled': self.two_factor_enabled,
            'preferred_language': self.preferred_language,
            'timezone': self.timezone,
            'currency': self.currency,
            'terms_accepted': self.terms_accepted,
            'privacy_policy_accepted': self.privacy_policy_accepted,
            'marketing_opt_in': self.marketing_opt_in,
            'is_active': self.is_active,
            'date_joined': self.date_joined.isoformat() if self.date_joined else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class UserProfile(models.Model):
    """Extended user profile for additional information"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('User')
    )
    
    # Personal information
    GENDER_CHOICES = (
        ('male', _('Male')),
        ('female', _('Female')),
        ('other', _('Other')),
        ('prefer_not_to_say', _('Prefer not to say')),
    )
    
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name=_('Gender')
    )
    
    # Location
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Address')
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('City')
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('State/Province')
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Country')
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Postal Code')
    )
    
    # Employment
    occupation = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Occupation')
    )
    company = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Company')
    )
    
    # Education
    education_level = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Education Level')
    )
    alma_mater = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Alma Mater')
    )
    
    # Social
    website = models.URLField(
        blank=True,
        null=True,
        verbose_name=_('Website')
    )
    bio = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Bio')
    )
    
    # Preferences
    theme = models.CharField(
        max_length=20,
        default='light',
        choices=(
            ('light', _('Light')),
            ('dark', _('Dark')),
            ('auto', _('Auto')),
        ),
        verbose_name=_('Theme')
    )
    notification_sound = models.BooleanField(
        default=True,
        verbose_name=_('Notification Sound')
    )
    email_digest_frequency = models.CharField(
        max_length=20,
        default='weekly',
        choices=(
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('monthly', _('Monthly')),
            ('never', _('Never')),
        ),
        verbose_name=_('Email Digest Frequency')
    )
    
    # Statistics
    login_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Login Count')
    )
    profile_views = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Profile Views')
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def __str__(self):
        return f"Profile of {self.user.email}"
    
    @property
    def full_address(self):
        """Get full formatted address"""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)
        return ', '.join(filter(None, parts))


class SocialAccount(models.Model):
    """Model for linking multiple social accounts to a single user"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='social_accounts',
        verbose_name=_('User')
    )
    
    provider = models.CharField(
        max_length=50,
        choices=User.SOCIAL_PROVIDERS,
        verbose_name=_('Provider')
    )
    uid = models.CharField(
        max_length=255,
        verbose_name=_('User ID')
    )
    
    # Provider-specific data
    access_token = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Access Token')
    )
    refresh_token = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Refresh Token')
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Expires At')
    )
    
    # Profile data
    profile_url = models.URLField(
        blank=True,
        null=True,
        verbose_name=_('Profile URL')
    )
    profile_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Profile Data')
    )
    
    # Metadata
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_('Is Primary')
    )
    verified = models.BooleanField(
        default=False,
        verbose_name=_('Verified')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Social Account')
        verbose_name_plural = _('Social Accounts')
        unique_together = ['provider', 'uid']
        indexes = [
            models.Index(fields=['provider', 'uid']),
            models.Index(fields=['user', 'provider']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.provider}"
    
    def clean(self):
        """Ensure only one primary account per provider per user"""
        if self.is_primary:
            existing_primary = SocialAccount.objects.filter(
                user=self.user,
                provider=self.provider,
                is_primary=True
            ).exclude(pk=self.pk)
            
            if existing_primary.exists():
                raise ValidationError(
                    f"User already has a primary {self.provider} account"
                )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class LoginHistory(models.Model):
    """Track user login history"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name=_('User')
    )
    
    # Login details
    ip_address = models.GenericIPAddressField(
        verbose_name=_('IP Address')
    )
    user_agent = models.TextField(
        verbose_name=_('User Agent')
    )
    
    # Location (populated via IP lookup)
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('City')
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Region')
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Country')
    )
    
    # Device info
    device_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Device Type')
    )
    browser = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Browser')
    )
    platform = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Platform')
    )
    
    # Authentication method
    auth_method = models.CharField(
        max_length=50,
        choices=(
            ('password', _('Password')),
            ('social', _('Social Login')),
            ('otp', _('OTP')),
            ('magic_link', _('Magic Link')),
            ('api_key', _('API Key')),
        ),
        default='password',
        verbose_name=_('Authentication Method')
    )
    
    # Status
    successful = models.BooleanField(
        default=True,
        verbose_name=_('Successful')
    )
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Failure Reason')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    class Meta:
        verbose_name = _('Login History')
        verbose_name_plural = _('Login History')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['auth_method']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.created_at}"


class EmailVerification(models.Model):
    """Email verification tokens"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verifications',
        verbose_name=_('User')
    )
    
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Token')
    )
    email = models.EmailField(
        verbose_name=_('Email')
    )
    
    # Status
    verified = models.BooleanField(
        default=False,
        verbose_name=_('Verified')
    )
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Verified At')
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        verbose_name=_('Expires At')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    class Meta:
        verbose_name = _('Email Verification')
        verbose_name_plural = _('Email Verifications')
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'verified']),
        ]
    
    def __str__(self):
        return f"Verification for {self.email}"
    
    @property
    def is_expired(self):
        """Check if verification token is expired"""
        return timezone.now() > self.expires_at


class PasswordResetToken(models.Model):
    """Password reset tokens"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name=_('User')
    )
    
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Token')
    )
    
    # Status
    used = models.BooleanField(
        default=False,
        verbose_name=_('Used')
    )
    used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Used At')
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        verbose_name=_('Expires At')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    class Meta:
        verbose_name = _('Password Reset Token')
        verbose_name_plural = _('Password Reset Tokens')
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'used']),
        ]
    
    def __str__(self):
        return f"Reset token for {self.user.email}"
    
    @property
    def is_expired(self):
        """Check if reset token is expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if reset token is valid (not used and not expired)"""
        return not self.used and not self.is_expired