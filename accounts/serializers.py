import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User

class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token

    def validate(self, attrs):
        identifier = attrs.get('username')
        if identifier and '@' in identifier:
            try:
                user = User.objects.get(Q(email__iexact=identifier) | Q(username__iexact=identifier))
                attrs['username'] = user.username
            except User.DoesNotExist:
                pass

        data = super().validate(attrs)
        data['id'] = self.user.id
        data['role'] = self.user.role
        data['username'] = self.user.username
        data['email'] = self.user.email or ''
        data['phone'] = self.user.phone or ''
        data['first_name'] = self.user.first_name or ''
        data['last_name'] = self.user.last_name or ''
        return data


class RegisterSerializer(serializers.ModelSerializer):
    access = serializers.SerializerMethodField(read_only=True)
    refresh = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "password",
            "phone",
            "first_name",
            "last_name",
            "role",
            "access",
            "refresh",
        ]

        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate_username(self, value):
        value = value.strip()
        if len(value) < 4 or len(value) > 30:
            raise serializers.ValidationError("Username must be between 4 and 30 characters.")
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return value

    def validate_phone(self, value):
        phone = re.sub(r'\D', '', str(value or ''))
        if len(phone) != 10:
            raise serializers.ValidationError("Phone number must contain 10 digits.")
        return phone

    def validate_first_name(self, value):
        value = value.strip()
        if len(value) < 2 or len(value) > 50:
            raise serializers.ValidationError("First name must be 2-50 characters.")
        return value

    def validate_last_name(self, value):
        value = value.strip()
        if len(value) < 2 or len(value) > 50:
            raise serializers.ValidationError("Last name must be 2-50 characters.")
        return value

    def get_access(self, obj):
        return str(RefreshToken.for_user(obj).access_token)

    def get_refresh(self, obj):
        return str(RefreshToken.for_user(obj))

    def create(self, validated_data):
        password = validated_data.pop("password", "123456") or "123456"
        validated_data.setdefault("role", "APPLICANT")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # create an applicant profile for applicant-role users so they appear in admin
        try:
            if getattr(user, 'role', None) == 'APPLICANT':
                # import locally to avoid circular imports at module load
                from applicants.models import Applicant
                Applicant.objects.get_or_create(user=user, defaults={
                    'job': None,
                    'cover_letter': '',
                })
        except Exception:
            # don't block user creation if applicant creation fails
            pass

        return user