from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    AcademicSession,
    AcademicSessionStatus,
    LecturerProfile,
    RosterImportBatch,
    RosterImportRow,
    StudentEnrollment,
    StudentRosterRecord,
    SupervisorAssignment,
    normalise_matric_number,
)
from .services import create_lecturer_account, register_student

User = get_user_model()


class AcademicSessionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True)

    class Meta:
        model = AcademicSession
        fields = [
            "id",
            "name",
            "status",
            "created_by_email",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "created_by_email",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]


class StudentRosterRecordSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = StudentRosterRecord
        fields = [
            "id",
            "session",
            "session_name",
            "matric_number",
            "first_name",
            "last_name",
            "other_names",
            "email",
            "phone",
            "is_eligible",
            "source",
            "created_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "source", "created_by_email", "created_at", "updated_at"]

    def validate_matric_number(self, value):
        value = normalise_matric_number(value)
        if not value:
            raise serializers.ValidationError("Matriculation number is required.")
        return value

    def validate(self, attrs):
        session = attrs.get("session", getattr(self.instance, "session", None))
        matric_number = attrs.get(
            "matric_number",
            getattr(self.instance, "matric_number", None),
        )
        if session and session.status == AcademicSessionStatus.CLOSED:
            raise serializers.ValidationError({"session": "Roster records cannot be changed in a closed session."})
        if self.instance and self.instance.enrollments.exists():
            if session != self.instance.session:
                raise serializers.ValidationError({"session": "The session cannot be changed after a student has enrolled against this roster record."})
            if matric_number != self.instance.matric_number:
                raise serializers.ValidationError({"matric_number": "The matriculation number cannot be changed after a student has enrolled against this roster record."})
        if session and matric_number:
            queryset = StudentRosterRecord.objects.filter(
                session=session,
                matric_number=matric_number,
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"matric_number": "This matriculation number already exists in the selected session."}
                )
        return attrs


class StudentRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=12, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    other_names = serializers.CharField(max_length=150, required=False, allow_blank=True)
    matric_number = serializers.CharField(max_length=40)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return value

    def validate_matric_number(self, value):
        value = normalise_matric_number(value)
        if not value:
            raise serializers.ValidationError("Matriculation number is required.")
        return value

    def validate(self, attrs):
        candidate = User(
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )
        validate_password(attrs["password"], user=candidate)
        return attrs

    def create(self, validated_data):
        return register_student(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            other_names=validated_data.get("other_names", ""),
            matric_number=validated_data["matric_number"],
        )


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="user.get_full_name", read_only=True)
    student_email = serializers.EmailField(source="user.email", read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    roster_record_eligible = serializers.BooleanField(
        source="roster_record.is_eligible",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StudentEnrollment
        fields = [
            "id",
            "student_name",
            "student_email",
            "session",
            "session_name",
            "roster_record",
            "roster_record_eligible",
            "matric_number",
            "other_names",
            "verification_status",
            "verification_method",
            "verified_at",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "created_at",
        ]
        read_only_fields = fields


class StudentEnrollmentReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[("approve", "Approve"), ("reject", "Reject")])
    notes = serializers.CharField(required=False, allow_blank=True, max_length=3000)

    def validate(self, attrs):
        if attrs["decision"] == "reject" and not attrs.get("notes", "").strip():
            raise serializers.ValidationError({"notes": "A reason is required when rejecting a registration."})
        return attrs


class LecturerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email")
    first_name = serializers.CharField(source="user.first_name", max_length=150)
    last_name = serializers.CharField(source="user.last_name", max_length=150)
    password = serializers.CharField(write_only=True, min_length=12, required=False)

    class Meta:
        model = LecturerProfile
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "staff_number",
            "designation",
            "phone",
            "office",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value):
        value = value.strip().lower()
        queryset = User.objects.filter(email__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.user_id)
        if queryset.exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return value

    def validate_staff_number(self, value):
        if value is None:
            return None
        value = value.strip().upper() or None
        if value:
            queryset = LecturerProfile.objects.filter(staff_number__iexact=value)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError("This staff number is already assigned to another lecturer.")
        return value

    def validate(self, attrs):
        user_data = attrs.get("user", {})
        password = attrs.get("password")
        if self.instance is None:
            if not password:
                raise serializers.ValidationError({"password": "An initial password is required."})
            candidate = User(
                email=user_data.get("email", ""),
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", ""),
            )
            validate_password(password, user=candidate)
        elif password:
            validate_password(password, user=self.instance.user)
        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        password = validated_data.pop("password")
        return create_lecturer_account(
            actor=self.context["request"].user,
            email=user_data["email"],
            password=password,
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            **validated_data,
        )

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        password = validated_data.pop("password", None)
        for field, value in user_data.items():
            setattr(instance.user, field, value)
        if password:
            instance.user.set_password(password)
        if user_data or password:
            instance.user.save()
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class SupervisorAssignmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student_enrollment.user.get_full_name", read_only=True)
    matric_number = serializers.CharField(source="student_enrollment.matric_number", read_only=True)
    session_name = serializers.CharField(source="student_enrollment.session.name", read_only=True)
    lecturer_name = serializers.CharField(source="lecturer.user.get_full_name", read_only=True)
    lecturer_email = serializers.EmailField(source="lecturer.user.email", read_only=True)
    assigned_by_email = serializers.EmailField(source="assigned_by.email", read_only=True)
    ended_by_email = serializers.EmailField(source="ended_by.email", read_only=True, allow_null=True)

    class Meta:
        model = SupervisorAssignment
        fields = [
            "id",
            "student_enrollment",
            "student_name",
            "matric_number",
            "session_name",
            "lecturer",
            "lecturer_name",
            "lecturer_email",
            "assigned_by_email",
            "assigned_at",
            "is_current",
            "ended_at",
            "ended_by_email",
            "reassignment_reason",
        ]
        read_only_fields = fields


class SupervisorAssignmentCreateSerializer(serializers.Serializer):
    student_enrollment = serializers.UUIDField()
    lecturer = serializers.UUIDField()


class SupervisorReassignmentSerializer(serializers.Serializer):
    lecturer = serializers.UUIDField()
    reason = serializers.CharField(max_length=3000, allow_blank=False, trim_whitespace=True)


class RosterImportPreviewSerializer(serializers.Serializer):
    session = serializers.PrimaryKeyRelatedField(queryset=AcademicSession.objects.all())
    file = serializers.FileField()


class RosterImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RosterImportRow
        fields = [
            "id",
            "row_number",
            "raw_data",
            "matric_number",
            "first_name",
            "last_name",
            "other_names",
            "email",
            "phone",
            "is_eligible",
            "status",
            "errors",
            "created_record",
        ]


class RosterImportBatchSerializer(serializers.ModelSerializer):
    rows = RosterImportRowSerializer(many=True, read_only=True)
    session_name = serializers.CharField(source="session.name", read_only=True)
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = RosterImportBatch
        fields = [
            "id",
            "session",
            "session_name",
            "original_file_name",
            "status",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "duplicate_rows",
            "imported_rows",
            "uploaded_by_email",
            "created_at",
            "committed_at",
            "rows",
        ]
        read_only_fields = fields


class StudentRegistrationStatusSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    student_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = [
            "id",
            "student_name",
            "matric_number",
            "session_name",
            "verification_status",
            "verification_method",
            "verified_at",
            "reviewed_at",
            "review_notes",
        ]
        read_only_fields = fields
