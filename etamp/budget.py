"""Code-enforced spend ledger for the $10 eTAMP validation study (guide section 3).

Each `python run.py` invocation is a separate process (the driver scripts loop
over task ids), so the ledger is a JSON file on disk, mutated under an flock,
rather than an in-memory counter.
"""
import fcntl
import json
import time
import uuid
import pathlib

LEDGER_PATH = pathlib.Path(__file__).resolve().parent / "spend_ledger.json"
HARD_CAP_USD = 9.0
IN_RATE_PER_M = 0.25   # conservative: assume every input token hits the cache-write rate
OUT_RATE_PER_M = 1.20
MAX_INPUT_TOKENS = 30_000
MAX_OUTPUT_TOKENS = 1_024


class BudgetExceeded(Exception):
    pass


class TokenLimitExceeded(Exception):
    pass


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * IN_RATE_PER_M + output_tokens * OUT_RATE_PER_M) / 1_000_000


def _load(f) -> dict:
    f.seek(0)
    raw = f.read()
    if not raw:
        return {"reservations": {}}
    return json.loads(raw)


def _save(f, ledger: dict) -> None:
    f.seek(0)
    f.truncate()
    f.write(json.dumps(ledger, indent=2))
    f.flush()


def _total_committed(ledger: dict) -> float:
    return sum(r["cost_usd"] for r in ledger["reservations"].values())


def reserve(input_tokens: int, output_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    """Check the input/output caps and the $9 ledger cap, then reserve the
    worst-case cost for this call before it is sent. Raises instead of
    truncating — an over-limit request must never be silently shortened."""
    if input_tokens > MAX_INPUT_TOKENS:
        raise TokenLimitExceeded(
            f"input_tokens={input_tokens} exceeds cap of {MAX_INPUT_TOKENS}; "
            "run marked unresolved, not sent"
        )
    if output_tokens > MAX_OUTPUT_TOKENS:
        raise TokenLimitExceeded(
            f"output_tokens={output_tokens} exceeds cap of {MAX_OUTPUT_TOKENS}"
        )
    worst_case = estimate_cost_usd(input_tokens, output_tokens)
    reservation_id = uuid.uuid4().hex

    LEDGER_PATH.touch(exist_ok=True)
    with LEDGER_PATH.open("r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            ledger = _load(f)
            spent = _total_committed(ledger)
            if spent + worst_case > HARD_CAP_USD:
                raise BudgetExceeded(
                    f"spent=${spent:.4f} + reserved=${worst_case:.4f} would "
                    f"exceed ${HARD_CAP_USD:.2f} cap; call refused"
                )
            ledger["reservations"][reservation_id] = {
                "status": "reserved",
                "cost_usd": worst_case,
                "input_tokens": input_tokens,
                "output_tokens_cap": output_tokens,
                "ts": time.time(),
            }
            _save(f, ledger)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return reservation_id


def commit(reservation_id: str, actual_input_tokens: int, actual_output_tokens: int) -> float:
    """Replace the worst-case reservation with the real cost from the API
    response's usage field. If the call errored/timed out before this is
    called, the original worst-case reservation stands (per guide: retain
    the reservation after a timeout, never quietly drop it)."""
    actual_cost = estimate_cost_usd(actual_input_tokens, actual_output_tokens)
    with LEDGER_PATH.open("r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            ledger = _load(f)
            ledger["reservations"][reservation_id] = {
                "status": "committed",
                "cost_usd": actual_cost,
                "input_tokens": actual_input_tokens,
                "output_tokens": actual_output_tokens,
                "ts": time.time(),
            }
            _save(f, ledger)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return actual_cost


def total_spent_usd() -> float:
    if not LEDGER_PATH.exists():
        return 0.0
    with LEDGER_PATH.open("r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            ledger = _load(f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return _total_committed(ledger)
