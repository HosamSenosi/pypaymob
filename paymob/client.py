from typing import Any
from paymob.connection import ConnectionPool
from paymob.exceptions import ValidationError
from paymob.utility import validate_email
from paymob.config import PaymobConfig
from paymob.auth_utility import PaymobAuth
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class PaymobTransaction:

    def __init__(self, connection_pool: ConnectionPool, config: PaymobConfig) -> None:
        self.config = config
        self.pool = connection_pool
        self.auth = PaymobAuth(config, connection_pool)

    def create_payment_intent(
        self,
        *,
        amount_cents: int,
        currency: str,
        payment_method_ids: list[int | str],
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        items: list[dict[str, str | int]] | None = None,
        special_reference: str | None = None,
        extras: dict[str, Any] | None = None,
        notification_url: str | None = None,
        redirection_url: str | None = None,
        billing_data: dict[str, str] | None = None,
        subscription_plan_id: str | None = None,
        subscription_start_date: str | None = None,
        expiration: int | None = None,
    ) -> dict[str, Any]:
        """
        # Create a payment intent.
        > You can find Paymob docs for this endpoint here: https://developers.paymob.com/egypt/api-reference-guide/create-intention-payment-api
        Args:
            [Required by Paymob]:
            amount_cents: Amount in cents
            currency: Currency of payment
            payment_method_ids: List of payment integration IDs or their names. ex: [1256, "card"]
            first_name: implemented as first_name in the billing_data object
            last_name: implemented as last_name in the billing_data object
            email: Email of the customer, implemented as email in the billing_data
            phone_number: implemented as phone_number in the billing_data
            [Optional]:
            items:
                item array is optional but if provided, both the name and amount fields are required.
                ex: {
                    "name": "Item name",
                    "amount": 2000,
                    "description": "Item description",
                    "quantity": 1 }
            special_reference: Unique special identifier or reference associated with a transaction or order.
                It can be used for tracking or categorizing specific types of transactions and it returns within the transaction callback under merchant_order_id.
            extras:  Can be used to send your own parameters and receive it in the callbacks. It will be found in the payment key claims object in the callback.
            notification_url: The webhook_url
            redirection_url: The redirection_url
            billing_data:
                expected keys: apartment, street, building, country, floor, state, city, postal_code, extra_description, shipping_method
            subscription_plan_id: To create a subscription, ID of the subscription plan is *Required for subscription*
            subscription_start_date (str: YYYY-MM-DD): Start subscription in future date *Optional for subscription*

        Returns:
            dict containing checkout_url and response
        """

        self.validate_payment_input(amount_cents, payment_method_ids, email)
        try:
            payment_method_ids = list(map(int, payment_method_ids))
        except:
            raise ValidationError("payment_method_ids must be a list of integers")

        # Required by Paymob
        payload = {
            "amount": amount_cents,
            "payment_methods": payment_method_ids,
            "currency": currency,
            "billing_data": {
                "first_name": first_name,
                "email": email,
                "phone_number": phone_number,
                "last_name": last_name,
            },
        }

        # Add optional params
        self._add_optional_payment_params(payload, locals())

        # Make request
        # This endpoint auth with the secret key
        headers = {
            "Authorization": f"Token {self.config.secret_key}",
            "Content-Type": "application/json",
        }

        response = self.pool.post("/v1/intention/", headers=headers, json=payload)

        response.raise_for_status()
        checkout_url = "https://accept.paymob.com/unifiedcheckout/?publicKey={self.config.public_key}&clientSecret={response['client_secret']}"
        logger.debug(f"Checkout URL: {checkout_url}")
        return {
            "checkout_url": checkout_url,
            "response": response,
        }

    @staticmethod
    def validate_payment_input(
        amount_cents: int, payment_method_ids: list[int | str], email: str
    ) -> None:
        if amount_cents <= 0:
            raise ValidationError(
                "Amount must be greater than 0", params={"amount_cents": amount_cents}
            )
        if not payment_method_ids:
            raise ValidationError(
                "At least one payment method (integration ID) required"
            )

        if not email:
            raise ValidationError("Email is required")
        validate_email(email)  # simple email validator

    @staticmethod
    def _add_optional_payment_params(
        payload: dict[str, Any], params: dict[str, Any]
    ) -> None:
        """
        Add optional params to the payload, and make some validations
        Raises:
            ValidationError
        """
        optional_params = [
            "subscription_plan_id",
            "subscription_start_date",
            "special_reference",
            "notification_url",
            "redirection_url",
            "extras",
            "billing_data",
            "expiration",
            "items",
        ]
        # optional params for billing_data
        billing_data_keys = [
            "apartment",
            "street",
            "building",
            "country",
            "floor",
            "state",
            "city",
            "postal_code",
            "extra_description",
            "shipping_method",
        ]

        for param in optional_params:
            if params.get(param):
                if param == "billing_data":
                    if type(params[param]) != dict:
                        raise ValidationError(
                            f"billing_data must be a dictionary, not {type(params[param])}"
                        )
                    payload["billing_data"].update(
                        {
                            k: v
                            for k, v in params["billing_data"].items()
                            if (k in billing_data_keys) and v
                        }
                    )
                    continue
                if param == "subscription_start_date":
                    try:
                        datetime.strptime(params[param], "%Y-%m-%d")
                    except ValueError:
                        raise ValidationError(
                            f"Invalid date format. Please use YYYY-MM-DD format."
                        )
                if param == "extras":
                    if type(params[param]) != dict:
                        raise ValidationError(
                            f"extras must be a dictionary, not {type(params[param])}"
                        )

                if param == "items":
                    if type(params[param]) != list:
                        raise ValidationError(
                            f"items must be a list, not {type(params[param])}"
                        )
                    # name and amount are required for each item
                    for item in params[param]:
                        if not item.get("name"):
                            raise ValidationError("Item name is required")
                        if not item.get("amount"):
                            raise ValidationError("Item amount is required")
                        if item.get("amount") <= 0:
                            raise ValidationError("Item amount must be greater than 0")

                payload[param] = params[param]

    def get_transaction_by_id(
        self, transaction_id: int, excuted: bool = False
    ) -> requests.Response:
        """
        Retrieve a transaction information by its ID
        In case of 403 error, the token will be froce refreshed and the request will be retried once
        """

        token = (
            self.auth.get_token()
            if not excuted
            else self.auth.get_token(force_refresh=True)
        )
        headers = {"Authorization": f"Bearer {token}"}
        response = self.pool.get(
            f"/api/acceptance/transactions/{transaction_id}", headers=headers
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403 and not excuted:
                return self.get_transaction_by_id(
                    transaction_id=transaction_id, excuted=True
                )
            raise e

        return response

    # TODO: Cache this for 2 minutes
    def get_transaction_by_ref(
        self, transaction_ref: str, excuted: bool = False
    ) -> requests.Response:
        """Retrieve a transaction information by its Special Reference (Merchant Order ID)"""

        token = (
            self.auth.get_token()
            if not excuted
            else self.auth.get_token(force_refresh=True)
        )
        headers = {"Authorization": f"Bearer {token}"}
        data = {"merchant_order_id": transaction_ref}

        response = self.pool.post(
            f"/api/ecommerce/orders/transaction_inquiry",
            headers=headers,
            json=data,
        )

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403 and not excuted:
                return self.get_transaction_by_ref(
                    transaction_ref=transaction_ref, excuted=True
                )
            raise e

        return response


