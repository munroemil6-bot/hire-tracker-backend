from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from .models import Notification
from .serializers import NotificationSerializer


def _is_admin(user):
    return user.is_staff or user.is_superuser or getattr(user, 'role', '') == 'ADMIN'


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if _is_admin(self.request.user):
            return queryset.order_by('-created_at')
        return queryset.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        if not _is_admin(request.user):
            return Response({'detail': 'Only admins can send notifications.'}, status=status.HTTP_403_FORBIDDEN)

        message = request.data.get('message', '').strip()
        kind = request.data.get('kind', 'GENERAL')
        recipient = request.data.get('recipient', 'all')
        user_id = request.data.get('user_id')

        if not message:
            return Response({'detail': 'Message is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if recipient == 'specific':
            if not user_id:
                return Response({'detail': 'user_id is required for specific recipient.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                target_user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
            notif = Notification.objects.create(user=target_user, message=message, kind=kind)
            return Response(NotificationSerializer(notif).data, status=status.HTTP_201_CREATED)
        else:
            recipients = User.objects.exclude(role='ADMIN')
            notifications = [Notification(user=u, message=message, kind=kind) for u in recipients]
            Notification.objects.bulk_create(notifications)
            return Response({'detail': f'Notification sent to {len(notifications)} users.'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def send_reminder(self, request):
        if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', '') == 'ADMIN'):
            return Response({'detail': 'Only admins can send reminders.'}, status=status.HTTP_403_FORBIDDEN)

        message = request.data.get('message', 'Please remember to clock in today.')
        for user in User.objects.filter(role='EMPLOYEE'):
            Notification.objects.create(user=user, message=message, kind='ATTENDANCE_REMINDER')
        return Response({'detail': 'Attendance reminders sent.'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def announce(self, request):
        if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', '') == 'ADMIN'):
            return Response({'detail': 'Only admins can send announcements.'}, status=status.HTTP_403_FORBIDDEN)

        message = request.data.get('message', 'Company announcement')
        for user in User.objects.exclude(role='ADMIN'):
            Notification.objects.create(user=user, message=message, kind='COMPANY_ANNOUNCEMENT')
        return Response({'detail': 'Announcement sent.'}, status=status.HTTP_201_CREATED)