from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class ProjFlowTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["full_name"] = user.get_full_name()
        token["roles"] = list(
            user.role_assignments.select_related("role").values_list("role__code", flat=True)
        )
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.pk),
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "full_name": self.user.get_full_name(),
            "roles": list(
                self.user.role_assignments.select_related("role").values_list(
                    "role__code",
                    flat=True,
                )
            ),
        }
        return data


class InitialAdministratorSetupSerializer(serializers.Serializer):
    setup_token = serializers.CharField(write_only=True, trim_whitespace=False)
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        min_length=12,
        max_length=128,
    )

    def validate_email(self, value):
        normalised_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalised_email).exists():
            raise serializers.ValidationError(
                "An account with this email address already exists."
            )
        return normalised_email

    def validate(self, attrs):
        candidate_user = User(
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )
        try:
            validate_password(attrs["password"], user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs
