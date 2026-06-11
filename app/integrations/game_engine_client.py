import httpx

from app.config import get_settings
from app.schemas.bot_action_schema import BotActionProposal
from app.schemas.bot_job_schema import BotTurnJob


class GameEngineApplicationError(Exception):
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        message = payload.get("message") or payload.get("error") or "main backend returned ok=false"
        super().__init__(str(message))


class BotTurnAlreadyProcessedError(GameEngineApplicationError):
    """Raised when the main backend reports the turn was already applied (idempotent duplicate)."""


def is_already_processed_payload(payload: dict) -> bool:
    message = str(payload.get("message") or payload.get("error") or "").lower()
    error_code = str(payload.get("errorCode") or "").upper()
    return (
        error_code
        in {
            "BOT_ACTION_ALREADY_PROCESSED",
            "ALREADY_PROCESSED",
            "TURN_ALREADY_PROCESSED",
        }
        or "already been processed" in message
        or "already processed" in message
    )


class GameEngineClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.service_token}"}

    @staticmethod
    def _success_payload(response: httpx.Response) -> dict:
        response.raise_for_status()
        payload = response.json() if response.content else {"ok": True}
        if isinstance(payload, dict) and payload.get("ok") is False:
            if is_already_processed_payload(payload):
                raise BotTurnAlreadyProcessedError(payload)
            raise GameEngineApplicationError(payload)
        return payload if isinstance(payload, dict) else {"ok": True, "data": payload}

    def check_bot_turn_validity(self, job: BotTurnJob) -> bool:
        payload = {
            "botId": job.bot_id,
            "tableId": job.table_id,
            "handId": job.hand_id,
            "turnId": job.turn_id,
            "legalActions": [action.value for action in job.legal_actions],
        }
        url = f"{self.settings.main_backend_url.rstrip('/')}/internal/bot-action/validate-turn"
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                response = client.post(url, json=payload, headers=self._headers())
            if response.status_code == 404:
                # Backends can omit the optional pre-flight endpoint; final action validation is still authoritative.
                return True
            if response.status_code >= 500:
                # Let the final send path raise/retry when the backend is temporarily unavailable.
                return True
            if response.status_code in {400, 403, 409, 410, 422}:
                return False
            response.raise_for_status()
            data = response.json()
            return bool(data.get("valid", True))
        except httpx.HTTPError:
            # Network errors are treated as unknown validity so the send path can use Celery retry handling.
            return True

    def send_bot_action(self, job: BotTurnJob, proposal: BotActionProposal) -> None:
        payload = {
            "botId": job.bot_id,
            "tableId": job.table_id,
            "handId": job.hand_id,
            "turnId": job.turn_id,
            "action": proposal.action.value,
        }
        if proposal.amount is not None:
            payload["amount"] = proposal.amount
        url = f"{self.settings.main_backend_url.rstrip('/')}/internal/bot-action"

        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=self._headers())
            self._success_payload(response)

    def request_bot_join(self, bot_id: str, table_id: str, preferred_seat: int | None = None) -> dict:
        payload = {
            "botId": bot_id,
            "tableId": table_id,
            "isBot": True,
        }
        if preferred_seat is not None:
            payload["preferredSeat"] = preferred_seat
        url = f"{self.settings.main_backend_url.rstrip('/')}/internal/bot-join"

        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=self._headers())
            return self._success_payload(response)

    def request_bot_leave(self, bot_id: str, table_id: str) -> dict:
        payload = {
            "botId": bot_id,
            "tableId": table_id,
            "isBot": True,
        }
        url = f"{self.settings.main_backend_url.rstrip('/')}/internal/bot-leave"

        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=self._headers())
            return self._success_payload(response)
