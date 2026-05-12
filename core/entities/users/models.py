from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from core.entities.common.models import Address, TimeStamp


class AdminUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The username must be set")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(username, password, **extra_fields)


class AdminUser(AbstractBaseUser, PermissionsMixin, TimeStamp):
    """Staff identities for django.contrib.admin only."""

    username = models.CharField(max_length=150, unique=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    new_password = models.CharField(max_length=128, blank=True)

    objects = AdminUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        app_label = "core"
        db_table = "admin_user"

    def save(self, *args, **kwargs):
        if self.new_password:
            self.set_password(self.new_password)
            self.new_password = ""
        super().save(*args, **kwargs)


class AccountManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser, TimeStamp):
    """End-user identity for APIs (manager, client storefront, member flows)."""

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        VERIFIED = "verified", _("Verified")

    class AccountType(models.TextChoices):
        CUSTOMER = "customer", _("Customer")
        MERCHANT = "merchant", _("Merchant")

    phone_number = PhoneNumberField(unique=True)
    email = models.EmailField(blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    gender = models.CharField(max_length=32, blank=True)
    address = models.OneToOneField(
        Address,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="account",
    )
    verification_status = models.CharField(
        max_length=32,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    account_type = models.CharField(
        max_length=32,
        choices=AccountType.choices,
        default=AccountType.CUSTOMER,
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    new_password = models.CharField(max_length=128, blank=True)

    objects = AccountManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        app_label = "core"
        db_table = "account"

    def save(self, *args, **kwargs):
        if self.new_password:
            self.set_password(self.new_password)
            self.new_password = ""
        super().save(*args, **kwargs)

    def is_manager_signup_profile_complete(self) -> bool:
        """Manager onboarding: require legal name and email before workspace setup."""
        if not (self.first_name or "").strip() or not (self.last_name or "").strip():
            return False
        return bool((self.email or "").strip())

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"
