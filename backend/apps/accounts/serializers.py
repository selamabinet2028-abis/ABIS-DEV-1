from django.contrib.auth import password_validation
from rest_framework import serializers

from apps.basedata.models import OrgUnit

from .models import Permission, Role, User, UserActivityLog


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        trim_whitespace=False, style={"input_type": "password"}
    )


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        trim_whitespace=False, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        trim_whitespace=False, style={"input_type": "password"}
    )

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        password_validation.validate_password(value, self.context["request"].user)
        return value


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "module"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SlugRelatedField(
        many=True,
        slug_field="codename",
        queryset=Permission.objects.all(),
        required=False,
    )
    user_count = serializers.IntegerField(source="users.count", read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "user_count"]


class UserSerializer(serializers.ModelSerializer):
    """Read shape — matches the frontend `User` type (role/org_unit as names)."""

    role = serializers.SerializerMethodField()
    role_id = serializers.PrimaryKeyRelatedField(source="role", read_only=True)
    org_unit = serializers.SerializerMethodField()
    org_unit_id = serializers.PrimaryKeyRelatedField(source="org_unit", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "role_id",
            "org_unit",
            "org_unit_id",
            "badge_number",
            "phone",
            "is_active",
            "must_change_password",
            "last_login",
            "date_joined",
        ]

    def get_role(self, obj: User) -> str | None:
        return obj.role_name

    def get_org_unit(self, obj: User) -> str | None:
        return obj.org_unit.name if obj.org_unit_id else None


class UserWriteSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), required=False, allow_null=True
    )
    org_unit = serializers.PrimaryKeyRelatedField(
        queryset=OrgUnit.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "org_unit",
            "badge_number",
            "phone",
            "is_active",
            "must_change_password",
        ]


class UserCreateSerializer(UserWriteSerializer):
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    class Meta(UserWriteSerializer.Meta):
        fields = UserWriteSerializer.Meta.fields + ["password"]

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(UserWriteSerializer):
    """Password changes go through /auth/password/change/ — never PATCH."""


class UserActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivityLog
        fields = [
            "id",
            "username",
            "action",
            "ip_address",
            "user_agent",
            "detail",
            "created_at",
        ]
