# The following code will be refactored for better error handling and configurability

import hmac
import hashlib
import logging
from typing import Any

from paymob.exceptions import APIException, ValidationError

logger = logging.getLogger(__name__)

PAYMOB_HMAC_SECRET_KEY = "" # Just a plcaeholder for now

class PaymobHmacAuth:
    """Methods to Handle Paymob HMAC authorization For callbacks"""

    @classmethod
    def authorize_hmac(
        cls,
        callback_data: dict[str, Any],
        query_params: dict[str, Any] | None,
        req_ip: str = "unknown",
    ) -> str | None:
        """
        Authorize Paymob callback with HMAC
        Args:
            request_obj: The callback request
        Returns:
            The type of the callback
        logs errors if HMAC verification fails
        """
        # Get hmac from either payload or query params
        # Paymob is inconsistent about that

        req_hmac = query_params.get("hmac", None) if query_params else None
        # Get request's hmac
        if callback_data.get("hmac", None):
            req_hmac = callback_data["hmac"]
        if not req_hmac:
            logger.error(
                f"Missing HMAC request received from ip: {req_ip}, \n data: {callback_data}"
            )
            return

        # Calculate hmac
        hmac_sk = cls._get_hmac_sk()
        concatenated_string, res_type = cls._concatenate(callback_data)
        logger.debug(f"Concatenated String: \n {concatenated_string}")

        if (not concatenated_string) or (res_type == "undefined"):
            # already logged, just return
            return
        calculated_hmac = hmac.new(
            hmac_sk.encode("utf-8"), concatenated_string.encode("utf-8"), hashlib.sha512
        )

        logger.debug(f"Calculated HMAC: \n {calculated_hmac.hexdigest()}")
        logger.debug(f"Received HMAC: \n {req_hmac}")
        # verify that both hmacs match
        if req_hmac != calculated_hmac.hexdigest():
            logger.error(
                f"Invalid HMAC received from ip: {req_ip}, \n data: {callback_data}"
            )
            return

        return res_type

    @classmethod
    def _concatenate(cls, callback_data: dict[str, Any]) -> tuple[str, str]:
        """
        Concatenate the Callback data depending on Callback type \n
        Args:
            callback_data: The callback data
        Returns:
            (concatenated_string, res_type): The concatenated string and the type of the callback
        """
        # idk why not just concatenate the whole data sorted! Why Paymob?!

        callback_type = cls._get_type_of_callback(callback_data)

        callback_type = callback_type.lower()

        if callback_type == "subscription":
            return cls._concatenate_subscription_callback(callback_data), callback_type

        elif callback_type == "transaction":
            return cls._concatenate_transaction_callback(callback_data), callback_type

        elif callback_type == "token":
            return cls._concatenate_token_callback(callback_data), callback_type

        elif callback_type == "undefined":
            logger.error(
                f"Cannot determine callback type, Ignoring ... \n data (payload): {callback_data}"
            )
            return ("", callback_type)
        else:
            logger.error(
                f"Unknown callback type: {callback_type}, Ignoring ... \n data (payload): {callback_data}"
            )
            return ("", "undefined")

    @staticmethod
    def _concatenate_transaction_callback(callback_data: dict[str, Any]) -> str:

        fields = [
            "amount_cents",
            "created_at",
            "currency",
            "error_occured",
            "has_parent_transaction",
            "id",
            "integration_id",
            "is_3d_secure",
            "is_auth",
            "is_capture",
            "is_refunded",
            "is_standalone_payment",
            "is_voided",
            "order.id",
            "owner",
            "pending",
            "source_data.pan",
            "source_data.sub_type",
            "source_data.type",
            "success",
        ]

        result = []
        for field in fields:
            # Handle nested dictionary access
            if "." in field:
                key1, key2 = field.split(".")
                value = callback_data["obj"].get(key1, {}).get(key2, "")
            else:
                value = callback_data["obj"].get(field, "")

            # Convert value to string and append to result
            if str(value) in ["True", "False"]:
                result.append(str(value).lower())
            elif str(value) == "None":
                result.append("null")
            else:
                result.append(str(value))

        # Join all values with empty string
        return "".join(result)

    @staticmethod
    def _concatenate_token_callback(callback_data: dict[str, Any]) -> str:
        fields = [
            "card_subtype",
            "created_at",
            "email",
            "id",
            "masked_pan",
            "merchant_id",
            "order_id",
            "token",
        ]

        result = []
        for field in fields:
            # Handle nested dictionary access
            if "." in field:
                key1, key2 = field.split(".")
                value = callback_data["obj"].get(key1, {}).get(key2, "")
            else:
                value = callback_data["obj"].get(field, "")

            # Convert value to string and append to result
            if str(value) in ["True", "False"]:
                result.append(str(value).lower())
            elif str(value) == "None":
                result.append("null")
            else:
                result.append(str(value))

        # Join all values with empty string
        return "".join(result)

    @staticmethod
    def _concatenate_subscription_callback(callback_data: dict[str, Any]) -> str:

        str1 = callback_data.get("trigger_type", "")
        str2 = callback_data.get("subscription_data", {}).get("id", "")

        if not str1 or not str2:
            raise ValidationError(
                "Cannot authorize callback: Not a valid subscription callback"
            )

        return "".join(str(str1) + "for" + str(str2))

    @staticmethod
    def _get_type_of_callback(callback_data: dict[str, Any]) -> str:
        """
        Returns the type of the webhook callback.
        Returns 'undefined' if unable to determine the type
        """
        if callback_data.get("type", None):
            return callback_data["type"]
        if callback_data.get("subscription_data", None):
            return "subscription"
        return "undefined"

    @staticmethod
    def _get_hmac_sk() -> str:
        sk = PAYMOB_HMAC_SECRET_KEY
        if not sk:
            raise APIException("Paymob HMAC secret key not configured")
        return sk

