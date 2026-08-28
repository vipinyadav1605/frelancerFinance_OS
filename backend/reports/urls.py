from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DashboardInsightsView, Gstr1ExportView, Gstr1SummaryView, Gstr3bSummaryView, ProfitLossExportView,
    ProfitLossReportView, ReportShareLinkViewSet, SharedReportView,
)

router = DefaultRouter()
router.register("report-share-links", ReportShareLinkViewSet, basename="report-share-link")

urlpatterns = [
    path("reports/profit-loss/", ProfitLossReportView.as_view(), name="report-profit-loss"),
    path("reports/profit-loss/export/", ProfitLossExportView.as_view(), name="report-profit-loss-export"),
    path("reports/gstr1-prefill/", Gstr1SummaryView.as_view(), name="report-gstr1-summary"),
    path("reports/gstr1-prefill/export/", Gstr1ExportView.as_view(), name="report-gstr1-export"),
    path("reports/gstr3b-summary/", Gstr3bSummaryView.as_view(), name="report-gstr3b-summary"),
    path("reports/insights/", DashboardInsightsView.as_view(), name="report-insights"),
    path("shared/report/<str:token>/", SharedReportView.as_view(), name="shared-report"),
] + router.urls
