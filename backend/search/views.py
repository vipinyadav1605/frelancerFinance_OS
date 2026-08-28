from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.models import Client
from invoicing.models import Invoice

MAX_RESULTS_PER_TYPE = 8
MIN_QUERY_LENGTH = 2


class GlobalSearchView(APIView):
    """Navbar search: finds invoices (by number or client name) and clients (by name)."""

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < MIN_QUERY_LENGTH:
            return Response({"results": []})

        invoices = Invoice.objects.filter(user=request.user).filter(
            Q(invoice_number__icontains=query) | Q(client_name_snapshot__icontains=query)
        )[:MAX_RESULTS_PER_TYPE]

        clients = Client.objects.filter(user=request.user, name__icontains=query)[:MAX_RESULTS_PER_TYPE]

        results = [
            {
                "type": "invoice",
                "label": f"{inv.invoice_number} - {inv.client_name_snapshot}",
                "link_path": f"/invoices/{inv.id}",
            }
            for inv in invoices
        ] + [
            {"type": "client", "label": client.name, "link_path": "/clients"}
            for client in clients
        ]
        return Response({"results": results})
