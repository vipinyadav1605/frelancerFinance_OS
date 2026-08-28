"""
Account deletion has to happen in dependency order: Client and
ExpenseCategory use on_delete=PROTECT on their children (Invoice/
RecurringInvoiceProfile, Expense) specifically so a client/category can't be
silently deleted out from under historical records - see clients/models.py
and expenses/models.py. That means deleting the user record straight away
would hit a ProtectedError, since Django's CASCADE from User would try to
delete Client/ExpenseCategory rows while PROTECT-ed children still point at
them. Deleting the protected children first, then the user (which cascades
everything else - clients, categories, business profile, API keys, etc.),
avoids that.
"""

from django.db import transaction

from expenses.models import Expense
from invoicing.models import Invoice, RecurringInvoiceProfile


@transaction.atomic
def delete_user_account(user) -> None:
    Invoice.objects.filter(user=user).delete()
    RecurringInvoiceProfile.objects.filter(user=user).delete()
    Expense.objects.filter(user=user).delete()
    user.delete()
