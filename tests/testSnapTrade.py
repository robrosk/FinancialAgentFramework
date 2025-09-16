import sys
import types
from typing import Any, Dict, List

import builtins
import pytest

import snapTrade as st


class DummySnapTradeClient:
    def __init__(self, client_id: str, consumer_key: str) -> None:
        self.client_id = client_id
        self.consumer_key = consumer_key

    # Methods used by SnapTradeService wrapper; tests will override as needed
    def register_user(self, user_id: str) -> Any:  # pragma: no cover - overridden per test
        return {"userSecret": "secret"}

    def get_user_login_redirect_uri(self, user_id: str, user_secret: str, **kwargs: Any) -> str:  # pragma: no cover
        return "https://example.com/login"

    def list_user_accounts(self, user_id: str, user_secret: str) -> List[Dict[str, Any]]:  # pragma: no cover
        return []

    def get_all_holdings(self, user_id: str, user_secret: str) -> Dict[str, Any]:  # pragma: no cover
        return {"data": []}

    def get_account_holdings(self, user_id: str, user_secret: str, account_id: str) -> Dict[str, Any]:  # pragma: no cover
        return {"data": []}


def test__get_env_required_missing_raises(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(RuntimeError):
        st._get_env("MISSING_VAR", required=True)


def test__get_env_required_false_returns_none(monkeypatch):
    monkeypatch.delenv("OPT_VAR", raising=False)
    assert st._get_env("OPT_VAR", required=False) is None


def test__get_env_returns_value(monkeypatch):
    monkeypatch.setenv("HAS_VAR", "value")
    assert st._get_env("HAS_VAR", required=True) == "value"


def test__load_env_if_available_calls_load_dotenv(monkeypatch):
    called = {"v": False}

    def fake_load_dotenv(override: bool = False):
        called["v"] = True

    monkeypatch.setattr(st, "load_dotenv", fake_load_dotenv)
    st._load_env_if_available()
    assert called["v"] is True


def test__import_snaptrade_client_success(monkeypatch):
    # Create a fake module 'snaptrade_client' with attribute SnapTrade
    fake_mod = types.ModuleType("snaptrade_client")
    setattr(fake_mod, "SnapTrade", DummySnapTradeClient)
    sys.modules["snaptrade_client"] = fake_mod
    try:
        SnapTrade = st._import_snaptrade_client()
        assert SnapTrade is DummySnapTradeClient
    finally:
        # Cleanup
        del sys.modules["snaptrade_client"]


def test__import_snaptrade_client_missing_raises(monkeypatch):
    if "snaptrade_client" in sys.modules:
        del sys.modules["snaptrade_client"]
    with pytest.raises(RuntimeError) as err:
        st._import_snaptrade_client()
    assert "pip install snaptrade-python-sdk" in str(err.value)


def test_SnapTradeService_call_first_available_success():
    class Obj:
        def a(self):  # pragma: no cover - called
            return "ok"

    assert st.SnapTradeService._call_first_available(Obj(), ["a", "b"]) == "ok"


def test_SnapTradeService_call_first_available_falls_through_then_works():
    class Obj:
        def a(self):
            raise ValueError("boom")

        def b(self):
            return "ok2"

    assert st.SnapTradeService._call_first_available(Obj(), ["a", "b"]) == "ok2"


def test_SnapTradeService_call_first_available_raises_when_none_present():
    class Obj:
        pass

    with pytest.raises(AttributeError):
        st.SnapTradeService._call_first_available(Obj(), ["x", "y"])


def test_SnapTradeService_init_uses_import(monkeypatch):
    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: DummySnapTradeClient)
    svc = st.SnapTradeService(client_id="cid", consumer_key="ck")
    assert isinstance(svc, st.SnapTradeService)


def test_register_user_dict_result(monkeypatch):
    class Client(DummySnapTradeClient):
        def register_user(self, user_id: str):
            return {"userSecret": "abc"}

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    assert svc.register_user("u1") == "abc"


def test_register_user_string_result(monkeypatch):
    class Client(DummySnapTradeClient):
        def register_user(self, user_id: str):
            return "xyz"

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    assert svc.register_user("u1") == "xyz"


def test_get_login_redirect_uri_variants(monkeypatch):
    class Client(DummySnapTradeClient):
        def get_login_redirect_uri(self, user_id: str, user_secret: str, **kwargs: Any) -> str:
            return "https://alt/login"

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    assert svc.get_login_redirect_uri("u", "s") == "https://alt/login"


def test_list_accounts_dict_wrapper(monkeypatch):
    class Client(DummySnapTradeClient):
        def list_user_accounts(self, user_id: str, user_secret: str):
            return {"accounts": [{"id": 1}, {"id": 2}]}

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    accounts = svc.list_accounts("u", "s")
    assert isinstance(accounts, list) and len(accounts) == 2


def test_list_accounts_list_passthrough(monkeypatch):
    class Client(DummySnapTradeClient):
        def list_user_accounts(self, user_id: str, user_secret: str):
            return [{"id": 3}]

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    accounts = svc.list_accounts("u", "s")
    assert accounts == [{"id": 3}]


def test_list_accounts_single_object(monkeypatch):
    class Client(DummySnapTradeClient):
        def list_user_accounts(self, user_id: str, user_secret: str):
            return {"id": 9}

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    accounts = svc.list_accounts("u", "s")
    assert accounts == [{"id": 9}]


def test_get_all_holdings_dict(monkeypatch):
    class Client(DummySnapTradeClient):
        def get_all_holdings(self, user_id: str, user_secret: str):
            return {"holdings": []}

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    assert svc.get_all_holdings("u", "s") == {"holdings": []}


def test_get_all_holdings_wrap(monkeypatch):
    class Client(DummySnapTradeClient):
        def get_all_holdings(self, user_id: str, user_secret: str):
            return [1, 2]

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    assert svc.get_all_holdings("u", "s") == {"data": [1, 2]}


def test_get_account_holdings_dict(monkeypatch):
    class Client(DummySnapTradeClient):
        def get_account_holdings(self, user_id: str, user_secret: str, account_id: str):
            return {"accountId": account_id, "positions": []}

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    assert svc.get_account_holdings("u", "s", "A1") == {"accountId": "A1", "positions": []}


def test_get_account_holdings_wrap(monkeypatch):
    class Client(DummySnapTradeClient):
        def get_account_holdings(self, user_id: str, user_secret: str, account_id: str):
            return ["pos"]

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    svc = st.SnapTradeService("cid", "ck")
    assert svc.get_account_holdings("u", "s", "A2") == {"data": ["pos"]}


def test_get_service_from_env(monkeypatch):
    monkeypatch.setenv("SNAPTRADE_CLIENT_ID", "cid")
    monkeypatch.setenv("SNAPTRADE_CONSUMER_KEY", "ck")
    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: DummySnapTradeClient)
    svc = st.get_service_from_env()
    assert isinstance(svc, st.SnapTradeService)


def test_filter_fidelity_accounts():
    accounts = [
        {"id": 1, "brokerage": "Fidelity Investments"},
        {"id": 2, "brokerageName": "Other"},
        {"id": 3, "brokerage": "FIDELITY"},
    ]
    out = st.filter_fidelity_accounts(accounts)
    assert [a["id"] for a in out] == [1, 3]


def test_ensure_user_uses_env(monkeypatch):
    monkeypatch.setenv("SNAPTRADE_CLIENT_ID", "cid")
    monkeypatch.setenv("SNAPTRADE_CONSUMER_KEY", "ck")
    monkeypatch.setenv("SNAPTRADE_USER_ID", "U")
    monkeypatch.setenv("SNAPTRADE_USER_SECRET", "S")
    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: DummySnapTradeClient)
    uid, sec = st.ensure_user()
    assert (uid, sec) == ("U", "S")


def test_ensure_user_registers_when_missing(monkeypatch):
    monkeypatch.setenv("SNAPTRADE_CLIENT_ID", "cid")
    monkeypatch.setenv("SNAPTRADE_CONSUMER_KEY", "ck")
    monkeypatch.delenv("SNAPTRADE_USER_ID", raising=False)
    monkeypatch.delenv("SNAPTRADE_USER_SECRET", raising=False)

    class Client(DummySnapTradeClient):
        def register_user(self, user_id: str):
            assert user_id.startswith("test-")
            return "sec"

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    # Freeze UUID
    class DummyUUID:
        def __init__(self, v):
            self.v = v

        def __str__(self):  # pragma: no cover - not used
            return self.v

    monkeypatch.setattr(st.uuid, "uuid4", lambda: "fixed")
    uid, sec = st.ensure_user()
    assert uid == "test-fixed"
    assert sec == "sec"


def test_get_fidelity_accounts_filters(monkeypatch):
    monkeypatch.setenv("SNAPTRADE_CLIENT_ID", "cid")
    monkeypatch.setenv("SNAPTRADE_CONSUMER_KEY", "ck")

    class Client(DummySnapTradeClient):
        def list_user_accounts(self, user_id: str, user_secret: str):
            return [
                {"id": 1, "brokerage": "Fidelity"},
                {"id": 2, "brokerageName": "Other"},
            ]

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    out = st.get_fidelity_accounts("U", "S")
    assert [a["id"] for a in out] == [1]


def test_get_fidelity_holdings_passthrough(monkeypatch):
    monkeypatch.setenv("SNAPTRADE_CLIENT_ID", "cid")
    monkeypatch.setenv("SNAPTRADE_CONSUMER_KEY", "ck")

    class Client(DummySnapTradeClient):
        def get_all_holdings(self, user_id: str, user_secret: str):
            return {"all": True}

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    out = st.get_fidelity_holdings("U", "S")
    assert out == {"all": True}


def test_get_connection_url_with_hint_then_fallback(monkeypatch):
    monkeypatch.setenv("SNAPTRADE_CLIENT_ID", "cid")
    monkeypatch.setenv("SNAPTRADE_CONSUMER_KEY", "ck")

    class Client(DummySnapTradeClient):
        calls = {"count": 0}

        def get_user_login_redirect_uri(self, user_id: str, user_secret: str, **kwargs: Any) -> str:
            Client.calls["count"] += 1
            if "brokerage" in kwargs:
                raise RuntimeError("unsupported kw")
            return "https://final/login"

    monkeypatch.setattr(st, "_import_snaptrade_client", lambda: Client)
    url = st.get_connection_url("U", "S")
    assert url == "https://final/login"


def test__print_err_writes_stderr(capsys):
    st._print_err("oops")
    captured = capsys.readouterr()
    assert captured.err.strip() == "oops"


