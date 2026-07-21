from rest_framework import serializers

from .models import Applicant


class ApplicantSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    job_title = serializers.SerializerMethodField(read_only=True)

    interview_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)

    class Meta:
        model = Applicant
        fields = [
            "id",
            "user",
            "user_name",
            "job",
            "job_title",
            "resume",
            "cover_letter",
            "application_status",
            "interview_date",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request is None or request.user is None or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required to apply")

        user = validated_data.pop("user", request.user)
        application_status = validated_data.pop("application_status", "PENDING")

        applicant = Applicant.objects.create(
            user=user,
            application_status=application_status,
            **validated_data,
        )

        return applicant

    def get_job_title(self, obj):
        return getattr(obj.job, 'title', '') if obj and getattr(obj, 'job', None) else ''
