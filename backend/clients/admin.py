from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "country", "is_international"]
    search_fields = ["name", "email", "user__email"]
    list_filter = ["is_international", "country"]
