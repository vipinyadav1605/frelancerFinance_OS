from rest_framework import serializers


class WaitlistSignupSerializer(serializers.Serializer):
    # Plain (not ModelSerializer) so re-submitting an already-waitlisted email
    # doesn't 400 on a uniqueness validator - the view treats it as an
    # idempotent "you're on the list" instead.
    email = serializers.EmailField()
