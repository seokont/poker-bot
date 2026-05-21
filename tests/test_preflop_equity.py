from app.decision.action_history import analyze_action_history
from app.decision.equity_calculator import calculate_hero_equity
from app.decision.hand_notation import combo_label, hole_cards_to_combo
from app.decision.omaha_preflop_charts import lookup_omaha_preflop_chart
from app.decision.preflop_charts import lookup_preflop_chart
from app.decision.range_estimator import estimate_villain_range
from app.schemas.bot_action_schema import BotAction
from app.schemas.bot_job_schema import BotTurnJob, PreviousAction
from app.schemas.game_state_schema import GameType, Position, Street
from pokerkit.analysis import parse_range


def _job(**overrides) -> BotTurnJob:
    payload = {
        "botId": "b1",
        "tableId": "t1",
        "handId": "h1",
        "turnId": "x1",
        "street": "PREFLOP",
        "gameType": "NLH",
        "botHoleCards": ["As", "Kd"],
        "boardCards": [],
        "potSize": 30,
        "currentBet": 20,
        "botStack": 1000,
        "botCurrentBet": 0,
        "bigBlind": 10,
        "position": "BTN",
        "activePlayersCount": 2,
        "legalActions": ["FOLD", "CALL", "RAISE"],
        "previousActions": [],
    }
    payload.update(overrides)
    return BotTurnJob.model_validate(payload)


def test_chart_open_btn_ak():
    job = _job(street="PREFLOP", currentBet=10, botCurrentBet=0, position="BTN")
    advice = lookup_preflop_chart(job)
    assert advice.action == "OPEN"


def test_chart_bb_defend_vs_steal():
    job = _job(
        position="BB",
        currentBet=25,
        botCurrentBet=0,
        activePlayersCount=2,
        previousActions=[
            {"playerId": "v1", "action": "RAISE", "amount": 25},
        ],
    )
    advice = lookup_preflop_chart(job)
    assert advice.action == "CALL"
    assert "steal" in advice.reason.lower()


def test_chart_three_bet_ip_spot():
    job = _job(
        position="BTN",
        currentBet=90,
        botCurrentBet=0,
        potSize=120,
        botHoleCards=["Ah", "Ad"],
    )
    advice = lookup_preflop_chart(job)
    assert advice.action in {"THREE_BET", "CALL"}


def test_omaha_chart_open():
    job = _job(
        gameType="OMAHA_4",
        botHoleCards=["As", "Ah", "Kd", "Kc"],
        street="PREFLOP",
        currentBet=10,
        botCurrentBet=0,
        position="BTN",
    )
    advice = lookup_omaha_preflop_chart(job)
    assert advice.action in {"OPEN", "CALL"}


def test_action_history_tight_range():
    job = _job(
        street="FLOP",
        boardCards=["Tc", "8d", "6h"],
        previousActions=[
            {"playerId": "v1", "action": "RAISE", "amount": 40},
            {"playerId": "v1", "action": "RAISE", "amount": 120},
        ],
    )
    insight = analyze_action_history(job)
    assert insight.range_spec is not None
    assert "QQ" in insight.range_spec or "TT" in insight.range_spec


def test_equity_with_history_source():
    job = _job(
        street="FLOP",
        botHoleCards=["Ah", "Ad"],
        boardCards=["Kc", "7d", "2h"],
        potSize=100,
        currentBet=50,
        botCurrentBet=0,
        previousActions=[
            {"playerId": "v1", "action": "BET", "amount": 50},
        ],
        legalActions=["FOLD", "CALL"],
    )
    equity, source = calculate_hero_equity(job)
    assert equity is not None
    assert equity > 0.5
    assert source in {"action_history", "heuristic"}


def test_hero_combo_in_chart_range():
    combo = hole_cards_to_combo(["Qs", "Js"])
    assert combo in parse_range("QJs,JTs,QTs+")
