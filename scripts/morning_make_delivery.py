"""Deliver through the existing Make gateway; never retry an uncertain POST."""
import requests

RUN_URL = "https://eu1.make.com/api/v2/scenarios/7813123/run"


class DeliveryUncertain(RuntimeError):
    def __init__(self, message, execution_id=None):
        super().__init__(message)
        self.execution_id = execution_id


def send_via_make(api_token: str, chat_id: str, text: str) -> tuple[int, str]:
    try:
        response = requests.post(
            RUN_URL,
            headers={"Authorization": f"Token {api_token}"},
            json={"responsive": True, "data": {
                "kind": "morning_greeting", "chat_id": chat_id,
                "morning_chat_id": chat_id, "text": text,
            }},
            timeout=55,
        )
    except requests.RequestException:
        raise DeliveryUncertain("Make request outcome unknown; inspect execution history before retry") from None
    if response.status_code != 200:
        raise DeliveryUncertain(f"Make HTTP {response.status_code}; delivery not confirmed")
    try:
        result = response.json()
    except ValueError:
        raise DeliveryUncertain("Make returned an unreadable response") from None
    if not isinstance(result, dict):
        raise DeliveryUncertain("Make response shape unknown")
    execution_id = result.get("executionId")
    output = result.get("outputs", result.get("output"))
    if str(result.get("status")) != "1" or not isinstance(output, dict):
        raise DeliveryUncertain("Make execution/output not confirmed", execution_id)
    try:
        message_id = int(output.get("message_id", 0))
    except (ValueError, TypeError):
        message_id = 0
    if output.get("status") != "sent" or message_id <= 0 or str(output.get("chat_id")) != chat_id:
        raise DeliveryUncertain("Make Telegram delivery not confirmed for intended recipient", execution_id)
    return message_id, str(execution_id or "")
