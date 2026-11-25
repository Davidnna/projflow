import uuid

from django.conf import settings
from django.apps import apps
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils import timezone


class RoleCode(models.TextChoices):
    ADMINISTRATOR = "administrator", "Administrator"
    PROJECT_COORDINATOR = "project_coordinator", "Project Coordinator"
    LECTURER = "lecturer", "Lecturer"
    STUDENT = "student", "Student"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = email.strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_superuser") is True:
            raise ValueError("Use create_superuser() for superuser accounts.")
        return self._create_user(email, password, **extra_fields)

    @transaction.atomic
    def create_superuser(self, email, password=None, **extra_fields):
        if password is None:
            raise ValueError("A superuser must have a password.")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields["is_staff"] is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        user = self._create_user(email, password, **extra_fields)
        role, _ = Role.objects.using(self._db).get_or_create(
            code=RoleCode.ADMINISTRATOR,
            defaults={
                "name": "Administrator",
                "description": "System administration and configuration.",
                "is_system": True,
            },
        )
        UserRole.objects.using(self._db).get_or_create(user=user, role=role)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"
        ordering = ["email"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_uniq")
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email

    def has_role(self, code):
        return self.role_assignments.filter(role__code=code).exists()

    def __str__(self):
        return self.email


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=40, choices=RoleCode.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_role"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="user_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_created",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_user_role"
        ordering = ["user__email", "role__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="accounts_unique_user_role",
            )
        ]

    def save(self, *args, **kwargs):
        if self.user_id and self.role_id:
            database = kwargs.get("using") or self._state.db or "default"
            role_code = Role.objects.using(database).filter(
                pk=self.role_id
            ).values_list("code", flat=True).first()
            incompatible_role = {
                RoleCode.STUDENT: RoleCode.LECTURER,
                RoleCode.LECTURER: RoleCode.STUDENT,
            }.get(role_code)
            has_incompatible_assignment = bool(
                incompatible_role
                and UserRole.objects.using(database).filter(
                    user_id=self.user_id,
                    role__code=incompatible_role,
                ).exclude(pk=self.pk).exists()
            )
            has_active_lecturer_profile = False
            has_student_enrollment = False
            if role_code == RoleCode.STUDENT:
                LecturerProfile = apps.get_model("academics", "LecturerProfile")
                has_active_lecturer_profile = LecturerProfile.objects.using(
                    database
                ).filter(user_id=self.user_id, is_active=True).exists()
            elif role_code == RoleCode.LECTURER:
                StudentEnrollment = apps.get_model("academics", "StudentEnrollment")
                has_student_enrollment = StudentEnrollment.objects.using(
                    database
                ).filter(user_id=self.user_id).exists()
            if (
                has_incompatible_assignment
                or has_active_lecturer_profile
                or has_student_enrollment
            ):
                raise ValidationError(
                    "Student accounts cannot hold Lecturer roles or active Lecturer profiles, and Lecturer accounts cannot be assigned the Student role."
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"
