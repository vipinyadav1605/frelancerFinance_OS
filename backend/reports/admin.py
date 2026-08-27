from django.contrib import admin

from .models import TaxEstimate


@admin.register(TaxEstimate)
class TaxEstimateAdmin(admin.ModelAdmin):
    list_display = ["user", "period_start", "period_end", "net_profit", "estimated_gst_liability", "estimated_income_tax"]
    list_filter = ["period_start"]
