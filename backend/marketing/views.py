from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import WaitlistSignup
from .serializers import WaitlistSignupSerializer


class WaitlistSignupView(APIView):
    """Landing page email capture - no login needed."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "waitlist"

    def post(self, request):
        serializer = WaitlistSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        WaitlistSignup.objects.get_or_create(email=serializer.validated_data["email"])
        return Response(
            {"detail": "You're on the list - we'll email you when it's ready."},
            status=status.HTTP_201_CREATED,
        )
