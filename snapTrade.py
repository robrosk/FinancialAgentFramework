import os
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

# Optional dotenv support for local development
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore


def _load_env_if_available() -> None:
    if load_dotenv is not None:
        # Load from .env if present
        load_dotenv(override=False)


def _get_env(name: str, required: bool = True) -> Optional[str]:
    value = os.getenv(name)
    if required and (value is None or value.strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_env_any(names: List[str], required: bool = True) -> Optional[str]:
    """Return the first non-empty value among the provided env var names.

    Raises if required and none are present.
    """
    for n in names:
        v = os.getenv(n)
        if v is not None and v.strip() != "":
            return v
    if required:
        raise RuntimeError(
            f"Missing required environment variable (any of): {', '.join(names)}"
        )
    return None


def _import_snaptrade_client():
    try:
        # Official SDK module reported on PyPI and docs
        from snaptrade_client import SnapTrade  # type: ignore
        return SnapTrade
    except Exception as import_error:
        raise RuntimeError(
            "snaptrade_client module not found. Please install the SDK: pip install snaptrade-python-sdk"
        ) from import_error


class SnapTradeService:
    """Thin wrapper around the SnapTrade Python SDK with resilient method names.

    This wrapper tolerates minor method-name differences across SDK versions by
    attempting several possible method names for common operations.
    """

    def __init__(self, client_id: str, consumer_key: str) -> None:
        SnapTrade = _import_snaptrade_client()
        self._client = SnapTrade(client_id=client_id, consumer_key=consumer_key)

    @staticmethod
    def _call_first_available(obj: Any, method_names: List[str], *args: Any, **kwargs: Any) -> Any:
        last_error: Optional[Exception] = None
        for method_name in method_names:
            method = getattr(obj, method_name, None)
            if callable(method):
                try:
                    return method(*args, **kwargs)
                except Exception as err:  # pragma: no cover - passthrough to next option
                    last_error = err
                    continue
        if last_error:
            raise last_error
        raise AttributeError(f"None of the methods exist on object: {method_names}")

    # --- Authentication & Connection ---
    def register_user(self, user_id: str) -> str:
        """Register a user and return the user_secret.

        SDKs may return dict with 'userSecret' or the secret string directly.
        """
        result = self._call_first_available(
            self._client,
            ["register_user", "create_user", "users_register"],
            user_id,
        )
        if isinstance(result, dict) and "userSecret" in result:
            return str(result["userSecret"])
        return str(result)

    def get_login_redirect_uri(self, user_id: str, user_secret: str, **kwargs: Any) -> str:
        """Return a URL for the user to connect brokerage accounts via SnapTrade portal."""
        # Try common method names observed in docs/examples
        result = self._call_first_available(
            self._client,
            [
                "get_user_login_redirect_uri",
                "get_login_redirect_uri",
                "login_snap_trade_user",
            ],
            user_id,
            user_secret,
            **kwargs,
        )
        return str(result)

    # --- Accounts & Holdings ---
    def list_accounts(self, user_id: str, user_secret: str) -> List[Dict[str, Any]]:
        result = self._call_first_available(
            self._client,
            ["list_user_accounts", "get_accounts", "list_accounts"],
            user_id,
            user_secret,
        )
        if isinstance(result, dict) and "accounts" in result:
            return list(result["accounts"])  # type: ignore
        if isinstance(result, list):
            return result
        return [result] if result is not None else []

    def get_all_holdings(self, user_id: str, user_secret: str) -> Dict[str, Any]:
        result = self._call_first_available(
            self._client,
            ["get_all_holdings", "get_user_holdings", "holdings"],
            user_id,
            user_secret,
        )
        if isinstance(result, dict):
            return result
        return {"data": result}

    def get_account_holdings(
        self, user_id: str, user_secret: str, account_id: str
    ) -> Dict[str, Any]:
        result = self._call_first_available(
            self._client,
            ["get_account_holdings", "get_user_holdings_for_account"],
            user_id,
            user_secret,
            account_id,
        )
        if isinstance(result, dict):
            return result
        return {"data": result}


def get_service_from_env() -> SnapTradeService:
    _load_env_if_available()
    client_id = _get_env_any(["SNAPTRADE_CLIENT_ID", "CLIENTID", "SNAPTRADE_CLIENTID"], required=True)  # type: ignore[arg-type]
    consumer_key = _get_env_any(["SNAPTRADE_CONSUMER_KEY", "SECRET", "SNAPTRADE_CONSUMERKEY"], required=True)  # type: ignore[arg-type]
    return SnapTradeService(client_id=client_id or "", consumer_key=consumer_key or "")


def filter_fidelity_accounts(accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for acct in accounts:
        brokerage_name = (
            str(acct.get("brokerage", "") or acct.get("brokerageName", "") or "").lower()
        )
        if "fidelity" in brokerage_name:
            matches.append(acct)
    return matches


def ensure_user(user_id: Optional[str] = None) -> Tuple[str, str]:
    """Ensure a SnapTrade user exists; returns (user_id, user_secret).

    - If SNAPTRADE_USER_ID and SNAPTRADE_USER_SECRET are set, use them.
    - Otherwise registers a new test user with a random UUID.
    """
    service = get_service_from_env()
    env_user_id = _get_env_any(["SNAPTRADE_USER_ID", "USER_ID"], required=False)
    env_user_secret = _get_env_any(["SNAPTRADE_USER_SECRET", "USER_SECRET"], required=False)

    if env_user_id:
        if not env_user_secret:
            raise RuntimeError(
                "USER_ID provided but USER_SECRET is missing. Set USER_SECRET or SNAPTRADE_USER_SECRET, "
                "or unset USER_ID to register a new test user."
            )
        return env_user_id, env_user_secret  # type: ignore[return-value]

    uid = user_id or f"test-{uuid.uuid4()}"
    secret = service.register_user(uid)
    return uid, secret


def get_fidelity_accounts(user_id: str, user_secret: str) -> List[Dict[str, Any]]:
    service = get_service_from_env()
    accounts = service.list_accounts(user_id, user_secret)
    return filter_fidelity_accounts(accounts)


def get_fidelity_holdings(user_id: str, user_secret: str) -> Dict[str, Any]:
    service = get_service_from_env()
    all_holdings = service.get_all_holdings(user_id, user_secret)
    # Optionally filter holdings to Fidelity accounts if the shape allows
    return all_holdings


def get_connection_url(user_id: str, user_secret: str) -> str:
    service = get_service_from_env()
    # brokerage optional hint; some SDK versions may accept parameters like broker or connectionType
    try:
        return service.get_login_redirect_uri(user_id, user_secret, brokerage="fidelity")
    except Exception:
        return service.get_login_redirect_uri(user_id, user_secret)


def _print_err(msg: str) -> None:
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    # Simple CLI demo
    try:
        _load_env_if_available()
        user_id_env = os.getenv("SNAPTRADE_USER_ID")
        user_secret_env = os.getenv("SNAPTRADE_USER_SECRET")

        if not user_id_env or not user_secret_env:
            print("Registering test user (set SNAPTRADE_USER_ID and SNAPTRADE_USER_SECRET to reuse)")
            user_id, user_secret = ensure_user()
        else:
            user_id, user_secret = user_id_env, user_secret_env

        url = get_connection_url(user_id, user_secret)
        print("Connection portal URL (open to connect Fidelity):")
        print(url)

        print("\nListing Fidelity accounts (if already connected):")
        fidelity_accounts = get_fidelity_accounts(user_id, user_secret)
        if not fidelity_accounts:
            print("No Fidelity accounts found or not connected yet.")
        else:
            for acct in fidelity_accounts:
                print(acct)

        print("\nFetching holdings (all accounts):")
        holdings = get_fidelity_holdings(user_id, user_secret)
        print(holdings)
    except Exception as e:
        _print_err(f"Error: {e}")
        sys.exit(1)