from django.urls import path

from .views import WaitlistSignupView

urlpatterns = [
    path("waitlist/", WaitlistSignupView.as_view(), name="waitlist-signup"),
]
