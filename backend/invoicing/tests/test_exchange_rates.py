from decimal import Decimal
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import TestCase

from invoicing.services.exchange_rates import fetch_exchange_rate_to_inr


class FetchExchangeRateToInrTests(TestCase):
    def tearDown(self):
        cache.clear()

    def test_inr_short_circuits_without_a_network_call(self):
        with patch("invoicing.services.exchange_rates.requests.get") as mock_get:
            rate = fetch_exchange_rate_to_inr("INR")
        self.assertEqual(rate, Decimal("1"))
        mock_get.assert_not_called()

    @patch("invoicing.services.exchange_rates.requests.get")
    def test_fetches_and_returns_rate_for_foreign_currency(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {"rates": {"INR": 83.25}})
        rate = fetch_exchange_rate_to_inr("USD")
        self.assertEqual(rate, Decimal("83.2500"))

    @patch("invoicing.services.exchange_rates.requests.get")
    def test_second_call_uses_cache_not_a_second_network_call(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {"rates": {"INR": 83.25}})
        fetch_exchange_rate_to_inr("USD")
        fetch_exchange_rate_to_inr("USD")
        self.assertEqual(mock_get.call_count, 1)
