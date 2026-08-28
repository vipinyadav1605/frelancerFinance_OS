from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Applied only to invoices/expenses (the two lists that actually grow
    large for an active freelancer) - not globally, so small collections
    (clients, recurring invoices, API keys, notifications) keep returning a
    plain array and don't need frontend changes.
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
