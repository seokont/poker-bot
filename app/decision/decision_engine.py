from app.bots.bot_profiles import BotProfile
from app.decision.postflop_decision import decide_postflop
from app.decision.preflop_decision import decide_preflop
from app.schemas.bot_action_schema import BotAction, BotActionProposal
from app.schemas.bot_job_schema import BotTurnJob
from app.schemas.game_state_schema import GameType, Street


class DecisionEngine:
    def decide(self, job: BotTurnJob, profile: BotProfile) -> BotActionProposal:
        if job.game_type not in {GameType.NO_LIMIT_HOLDEM, GameType.NLH, GameType.TEXAS_HOLDEM}:
            return self.safe_default(job, f"Unsupported game type {job.game_type}")
        if job.street == Street.PREFLOP:
            return decide_preflop(job, profile)
        return decide_postflop(job, profile)

    @staticmethod
    def safe_default(job: BotTurnJob, reason: str = "Safe fallback") -> BotActionProposal:
        if BotAction.CHECK in job.legal_actions:
            return BotActionProposal(action=BotAction.CHECK, amount=None, reason=reason)
        if BotAction.FOLD in job.legal_actions:
            return BotActionProposal(action=BotAction.FOLD, amount=None, reason=reason)
        action = job.legal_actions[0]
        amount = None if action in {BotAction.CHECK, BotAction.FOLD} else max(0, job.current_bet - job.bot_current_bet)
        return BotActionProposal(action=action, amount=amount, reason=reason)
