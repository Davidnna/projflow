from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


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
