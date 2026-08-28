from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from expenses.models import Expense

from .models import ReportShareLink
from .serializers import (
    PeriodQuerySerializer, ReportShareLinkCreateSerializer, ReportShareLinkSerializer,
    TaxEstimateSerializer,
)
from .services.export import export_gstr1_csv, export_profit_loss_csv, export_profit_loss_pdf
from .services.gstr1 import compute_gstr1_prefill
from .services.gstr3b import compute_gstr3b_summary
from .services.insights import expense_breakdown_by_category, monthly_revenue_trend, top_clients_by_revenue
from .services.profit_loss import compute_profit_loss


class ProfitLossReportView(APIView):
    """FR (Phase 3): monthly/quarterly P&L + GST + income tax estimate."""

    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        estimate = compute_profit_loss(
            request.user, query.validated_data["period_start"], query.validated_data["period_end"]
        )
        return Response(TaxEstimateSerializer(estimate).data)


class ProfitLossExportView(APIView):
    """FR (Phase 3): export P&L + expense detail as CSV or PDF for the user's CA."""

    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        period_start = query.validated_data["period_start"]
        period_end = query.validated_data["period_end"]
        # Named "export_format", not "format" - DRF reserves the "format" query
        # param for its own content-negotiation (it maps to a renderer's
        # .format attribute and raises Http404 if none match, which is
        # confusingly surfaced as a 404 on this endpoint if you use "format").
        export_format = request.query_params.get("export_format", "csv").lower()

        estimate = compute_profit_loss(request.user, period_start, period_end)
        expenses = Expense.objects.filter(
            user=request.user, expense_date__gte=period_start, expense_date__lte=period_end
        ).select_related("category")

        filename = f"profit-loss_{period_start}_to_{period_end}"
        if export_format == "pdf":
            content = export_profit_loss_pdf(estimate, expenses)
            response = HttpResponse(content, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
        else:
            content = export_profit_loss_csv(estimate, expenses)
            response = HttpResponse(content, content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response


class Gstr1SummaryView(APIView):
    """FR (Phase 4): GSTR-1 pre-fill summary (B2B / B2C / Exports invoice buckets)."""

    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        data = compute_gstr1_prefill(
            request.user, query.validated_data["period_start"], query.validated_data["period_end"]
        )
        return Response({
            "period_start": data["period_start"],
            "period_end": data["period_end"],
            "b2b_totals": data["b2b_totals"],
            "b2c_totals": data["b2c_totals"],
            "exports_totals": data["exports_totals"],
        })


class Gstr1ExportView(APIView):
    """FR (Phase 4): downloadable GSTR-1 pre-fill worksheet, for manual filing on the GST portal."""

    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        period_start = query.validated_data["period_start"]
        period_end = query.validated_data["period_end"]

        data = compute_gstr1_prefill(request.user, period_start, period_end)
        content = export_gstr1_csv(data)
        filename = f"gstr1-prefill_{period_start}_to_{period_end}.csv"
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class Gstr3bSummaryView(APIView):
    """GSTR-3B pre-fill summary: outward taxable/zero-rated supplies, eligible ITC, net tax payable."""

    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        data = compute_gstr3b_summary(
            request.user, query.validated_data["period_start"], query.validated_data["period_end"]
        )
        return Response(data)


class DashboardInsightsView(APIView):
    """Chart data for the Dashboard: revenue trend, expense breakdown, top clients."""

    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        period_start = query.validated_data["period_start"]
        period_end = query.validated_data["period_end"]

        return Response({
            "monthly_revenue_trend": monthly_revenue_trend(request.user),
            "expense_breakdown": expense_breakdown_by_category(request.user, period_start, period_end),
            "top_clients": top_clients_by_revenue(request.user, period_start, period_end),
        })


class ReportShareLinkViewSet(viewsets.ModelViewSet):
    """Phase 5: create/list/revoke expiring read-only report share links."""

    serializer_class = ReportShareLinkSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return ReportShareLink.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return ReportShareLinkCreateSerializer
        return ReportShareLinkSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        link = serializer.save()
        return Response(ReportShareLinkSerializer(link).data, status=status.HTTP_201_CREATED)


class SharedReportView(APIView):
    """
    Phase 5: public (no login) read-only view of a shared report, for a CA or
    collaborator who doesn't have - and doesn't need - an account.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_view"

    def get(self, request, token):
        link = get_object_or_404(ReportShareLink, token=token)
        if link.is_expired:
            return Response({"detail": "This share link has expired."}, status=status.HTTP_410_GONE)

        estimate = compute_profit_loss(link.user, link.period_start, link.period_end)
        gstr1 = compute_gstr1_prefill(link.user, link.period_start, link.period_end)
        gstr3b = compute_gstr3b_summary(link.user, link.period_start, link.period_end)
        return Response({
            "label": link.label,
            "business_name": getattr(link.user.business_profile, "business_name", ""),
            "report": TaxEstimateSerializer(estimate).data,
            "gstr1_summary": {
                "b2b_totals": gstr1["b2b_totals"],
                "b2c_totals": gstr1["b2c_totals"],
                "exports_totals": gstr1["exports_totals"],
            },
            "gstr3b_summary": gstr3b,
        })
