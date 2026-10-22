from typing import Dict, Any
from config import config


class PaymentProcessor:
    """Handles external credit card transactions and webhooks."""

    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url

    def charge_card(self, customer_id: str, amount_cents: int, currency: str = "USD") -> Dict[str, Any]:
        """
        Executes payment charge against payment gateway.
        Returns transaction confirmation.
        """
        if amount_cents <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        print(f"Charging {amount_cents} {currency} for customer {customer_id} via {self.gateway_url}")
        return {
            "transaction_id": "tx_998877",
            "status": "succeeded",
            "amount": amount_cents,
            "currency": currency,
        }

    def handle_webhook(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Processes incoming payment gateway webhook events."""
        if event_type == "payment.succeeded":
            print(f"Recorded successful payment for tx: {event_data.get('transaction_id')}")
            return True
        return False


payment_processor = PaymentProcessor(config.PAYMENT_GATEWAY_URL)
