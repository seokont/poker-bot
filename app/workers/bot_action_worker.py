import random
import time

from sqlalchemy.orm import Session

from app.bots.bot_manager import BotManager
from app.bots.bot_statistics import record_bot_action_stats
from app.config import get_settings
from app.decision.decision_engine import DecisionEngine
from app.decision.randomness import occasional_slowdown_ms
from app.integrations.database import SessionLocal, create_database_tables
from app.integrations.game_engine_client import BotTurnAlreadyProcessedError, GameEngineClient
from app.integrations.redis_client import get_redis_client, set_json
from app.models.bot_action_log_model import BotActionLogModel
from app.redis.locks import acquire_bot_turn_lock, release_bot_turn_lock, sent_action_key
from app.schemas.bot_action_schema import BotAction, BotActionProposal
from app.schemas.bot_job_schema import BotTurnJob
from app.schemas.game_state_schema import Street
from app.workers.celery_app import celery_app
from app.workers.job_normalizer import normalize_backend_queue_job


@celery_app.task(name="process_bot_action", bind=True, max_retries=3, default_retry_delay=2)
def process_bot_action(self, payload: dict) -> dict:
    job = normalize_backend_queue_job(payload)
    return process_bot_turn_job(job, retry_callback=lambda exc: self.retry(exc=exc))


def process_bot_turn_job(job: BotTurnJob, retry_callback=None) -> dict:
    settings = get_settings()
    redis_client = get_redis_client()
    sent_key = sent_action_key(job.bot_id, job.hand_id, job.turn_id)

    if redis_client.exists(sent_key):
        return {"status": "duplicate_ignored", "botId": job.bot_id, "turnId": job.turn_id}

    create_database_tables()
    db = SessionLocal()
    lock_acquired = False
    try:
        manager = BotManager(db)
        profile = manager.get_or_create_profile(job.bot_id)
        if not profile.is_enabled:
            return {"status": "disabled", "botId": job.bot_id}

        delay_ms = calculate_thinking_delay_ms(job, profile)
        lock_ttl_seconds = max(settings.bot_lock_ttl_seconds, int(delay_ms / 1000) + 45)
        lock_acquired = wait_for_turn_lock(
            redis_client,
            job.bot_id,
            job.hand_id,
            job.turn_id,
            sent_key,
            lock_ttl_seconds,
            settings.bot_turn_lock_wait_seconds,
        )
        if redis_client.exists(sent_key):
            return {"status": "duplicate_ignored", "botId": job.bot_id, "turnId": job.turn_id}

        set_json(
            redis_client,
            f"bot:{job.bot_id}:state",
            {
                "botId": job.bot_id,
                "isBot": True,
                "enabled": True,
                "status": "thinking",
                "tableId": job.table_id,
                "handId": job.hand_id,
                "turnId": job.turn_id,
                "thinkingDelayMs": delay_ms,
            },
            ttl_seconds=max(15, int(delay_ms / 1000) + 30),
        )
        time.sleep(delay_ms / 1000)

        if redis_client.exists(sent_key):
            return {"status": "duplicate_ignored", "botId": job.bot_id, "turnId": job.turn_id}

        client = GameEngineClient()
        validate_ok = client.check_bot_turn_validity(job)
        if not validate_ok:
            log_action(
                db,
                job,
                DecisionEngine.safe_default(job, "validate-turn rejected; still attempting send").model_dump(
                    mode="json"
                ),
                "VALIDATE_WARN",
                delay_ms,
                profile.profile_type.value,
            )

        try:
            proposal = DecisionEngine().decide(job, profile)
        except Exception:
            proposal = DecisionEngine.safe_default(job, "Decision failed, using safe fallback")
        proposal = normalize_proposal_for_table(job, proposal)

        try:
            send_status = send_bot_action_with_retries(
                client,
                job,
                proposal,
                max_attempts=settings.bot_action_send_retries,
                retry_callback=retry_callback,
            )
        except Exception as exc:
            log_action(db, job, proposal.model_dump(mode="json"), "SEND_FAILED", delay_ms, profile.profile_type.value)
            if retry_callback is not None:
                raise retry_callback(exc)
            raise
        log_status = "ALREADY_PROCESSED" if send_status == "already_processed" else "SENT"
        redis_client.set(sent_key, "1", ex=lock_ttl_seconds)
        set_json(
            redis_client,
            f"recent:bot:{job.bot_id}:actions",
            {"handId": job.hand_id, "turnId": job.turn_id, "action": proposal.action.value, "amount": proposal.amount},
            ttl_seconds=3600,
        )
        log_action(db, job, proposal.model_dump(mode="json"), log_status, delay_ms, profile.profile_type.value)
        record_bot_action_stats(db, job, proposal.action)
        set_json(
            redis_client,
            f"bot:{job.bot_id}:state",
            {
                "botId": job.bot_id,
                "isBot": True,
                "enabled": True,
                "status": "acted",
                "tableId": job.table_id,
                "handId": job.hand_id,
                "turnId": job.turn_id,
                "lastAction": proposal.action.value,
            },
            ttl_seconds=3600,
        )
        return {
            "status": send_status,
            "botId": job.bot_id,
            "turnId": job.turn_id,
            "action": proposal.action.value,
            "amount": proposal.amount,
            "delayMs": delay_ms,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        if lock_acquired:
            release_bot_turn_lock(redis_client, job.bot_id, job.hand_id, job.turn_id)
        db.close()


def wait_for_turn_lock(
    redis_client,
    bot_id: str,
    hand_id: str,
    turn_id: str,
    sent_key: str,
    lock_ttl_seconds: int,
    max_wait_seconds: int,
) -> bool:
    deadline = time.monotonic() + max_wait_seconds
    while time.monotonic() < deadline:
        if redis_client.exists(sent_key):
            return False
        if acquire_bot_turn_lock(redis_client, bot_id, hand_id, turn_id, ttl_seconds=lock_ttl_seconds):
            return True
        time.sleep(0.25)
    return acquire_bot_turn_lock(redis_client, bot_id, hand_id, turn_id, ttl_seconds=lock_ttl_seconds)


def send_bot_action_with_retries(
    client: GameEngineClient,
    job: BotTurnJob,
    proposal: BotActionProposal,
    max_attempts: int,
    retry_callback=None,
) -> str:
    last_exc: Exception | None = None
    for attempt in range(max(1, max_attempts)):
        try:
            client.send_bot_action(job, proposal)
            return "sent"
        except BotTurnAlreadyProcessedError:
            return "already_processed"
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(min(5.0, 1.0 * (attempt + 1)))
                continue
            if retry_callback is not None:
                raise retry_callback(exc)
            raise last_exc
    if last_exc is not None:
        raise last_exc
    return "sent"


def calculate_thinking_delay_ms(job: BotTurnJob, profile) -> int:
    call_pressure = max(0, job.current_bet - job.bot_current_bet)
    all_in_or_big_pot = "ALL_IN" in [action.value for action in job.legal_actions] and (
        call_pressure >= job.bot_stack or job.pot_size >= job.bot_stack
    )
    hard = job.street in {Street.TURN, Street.RIVER} and call_pressure > job.pot_size * 0.4
    normal = job.street != Street.PREFLOP or call_pressure > 0
    if all_in_or_big_pot:
        base = random.randint(3000, 9000)
    elif hard:
        base = random.randint(5000, 8000)
    elif normal:
        base = random.randint(2000, 4000)
    else:
        base = random.randint(800, 1500)
    return min(profile.thinking_max_ms + 2500, max(profile.thinking_min_ms, base + occasional_slowdown_ms(profile)))


def normalize_proposal_for_table(job: BotTurnJob, proposal: BotActionProposal) -> BotActionProposal:
    if proposal.action not in job.legal_actions:
        return safe_legal_fallback(job, f"{proposal.reason}; action was outside legalActions")

    if proposal.action in {BotAction.CHECK, BotAction.FOLD}:
        return proposal.model_copy(update={"amount": None})

    if proposal.action == BotAction.CALL:
        amount = min(job.bot_stack, max(0, job.current_bet - job.bot_current_bet))
        if amount <= 0 and BotAction.CHECK in job.legal_actions:
            return BotActionProposal(action=BotAction.CHECK, amount=None, reason=f"{proposal.reason}; no chips needed to call")
        return proposal.model_copy(update={"amount": amount})

    if proposal.action == BotAction.RAISE:
        min_raise = job.min_raise or max(1, job.current_bet)
        min_raise_to = job.current_bet + min_raise
        max_total_bet = job.bot_current_bet + job.bot_stack
        amount = max(proposal.amount or 0, min_raise_to)
        if job.max_raise is not None:
            amount = min(amount, job.max_raise)
        amount = min(amount, max_total_bet)
        if amount <= job.current_bet:
            if BotAction.CALL in job.legal_actions:
                return BotActionProposal(
                    action=BotAction.CALL,
                    amount=min(job.bot_stack, max(0, job.current_bet - job.bot_current_bet)),
                    reason=f"{proposal.reason}; downgraded because raise size was not legal",
                )
            return DecisionEngine.safe_default(job, "Raise size was not legal")
        return proposal.model_copy(update={"amount": amount})

    if proposal.action == BotAction.BET:
        amount = max(proposal.amount or 0, job.min_raise or 1)
        if job.max_raise is not None:
            amount = min(amount, job.max_raise)
        amount = min(amount, job.bot_stack)
        if amount <= 0:
            return safe_legal_fallback(job, f"{proposal.reason}; bet amount was not valid")
        return proposal.model_copy(update={"amount": amount})

    if proposal.action == BotAction.ALL_IN:
        amount = min(proposal.amount or job.bot_stack, job.bot_stack)
        if amount <= 0:
            return safe_legal_fallback(job, f"{proposal.reason}; all-in amount was not valid")
        return proposal.model_copy(update={"amount": amount})

    return proposal


def safe_legal_fallback(job: BotTurnJob, reason: str) -> BotActionProposal:
    if BotAction.CHECK in job.legal_actions:
        return BotActionProposal(action=BotAction.CHECK, amount=None, reason=reason)
    if BotAction.FOLD in job.legal_actions:
        return BotActionProposal(action=BotAction.FOLD, amount=None, reason=reason)
    if BotAction.CALL in job.legal_actions:
        return BotActionProposal(action=BotAction.CALL, amount=min(job.bot_stack, max(0, job.current_bet - job.bot_current_bet)), reason=reason)

    action = job.legal_actions[0]
    if action in {BotAction.BET, BotAction.RAISE}:
        min_amount = job.current_bet + (job.min_raise or job.big_blind) if action == BotAction.RAISE else (job.min_raise or 1)
        return BotActionProposal(action=action, amount=min(job.bot_stack + job.bot_current_bet, min_amount), reason=reason)
    if action == BotAction.ALL_IN:
        return BotActionProposal(action=action, amount=job.bot_stack, reason=reason)
    return BotActionProposal(action=action, amount=None, reason=reason)


def log_action(db: Session, job: BotTurnJob, proposal: dict, status: str, decision_time_ms: int, profile_type: str) -> None:
    db.add(
        BotActionLogModel(
            bot_id=job.bot_id,
            table_id=job.table_id,
            hand_id=job.hand_id,
            turn_id=job.turn_id,
            street=job.street.value,
            action=proposal["action"],
            amount=proposal["amount"],
            reason=proposal["reason"],
            decision_time_ms=decision_time_ms,
            status=status,
            payload={
                "profile": profile_type,
                "inputSummary": {
                    "street": job.street.value,
                    "potSize": job.pot_size,
                    "currentBet": job.current_bet,
                    "botStack": job.bot_stack,
                    "activePlayersCount": job.active_players_count,
                    "legalActions": [action.value for action in job.legal_actions],
                },
                "job": job.model_dump(by_alias=True, mode="json"),
            },
        )
    )
    db.commit()
