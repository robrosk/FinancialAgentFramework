## Financial Agent Framework

An extendable framework for AI-driven financial agents. Agents are given tools to reason about markets, retrieve data, and act via third-party APIs. Initial tools include a SnapTrade integration for brokerage account data (e.g., Fidelity), web scraping utilities, and MCP-backed providers for real-time and historical market information.

### Goals
- Empower agents to analyze, plan, and execute financial tasks with auditable steps
- Provide a simple tool interface so you can plug in new data sources and actions
- Keep credentials secure and configuration simple (env-first design)

## Architecture

- **Agent Orchestrator**: Runs reasoning loops, selects tools, and composes results
- **Tooling Layer**: Individual tools with clear, minimal interfaces
  - `snapTrade.py`: access to connected brokerage accounts via SnapTrade (read-only)
  - Web scraping and content extraction
  - HTTP/data loaders for APIs and documents
  - MCP integrations for market data providers
- **Knowledge & Memory**: Optional vector stores and caches (planned)
- **Evaluation**: Tests, mock providers, and reproducible runs

## Tools

### SnapTrade (Brokerage Accounts)
- File: `snapTrade.py`
- Purpose: Authenticate via SnapTrade, generate connection portal links, and fetch account info/holdings (supports Fidelity and others via SnapTrade)
- Status: Read-only data access; trading actions not enabled

Key functions:
- `ensure_user(user_id: Optional[str]) -> (user_id, user_secret)`
- `get_connection_url(user_id, user_secret) -> str`
- `get_fidelity_accounts(user_id, user_secret) -> List[Dict]`
- `get_fidelity_holdings(user_id, user_secret) -> Dict`

Environment variables (aliases supported):
- Client ID: `SNAPTRADE_CLIENT_ID` or `CLIENTID` (also `SNAPTRADE_CLIENTID`)
- Consumer Key: `SNAPTRADE_CONSUMER_KEY` or `SECRET` (also `SNAPTRADE_CONSUMERKEY`)
- User ID: `SNAPTRADE_USER_ID` or `USER_ID`
- User Secret: `SNAPTRADE_USER_SECRET` or `USER_SECRET`

Behavior notes:
- If `USER_ID` is set, `USER_SECRET` must also be set (no auto-registration)
- If neither is set, a test user is registered automatically for local dev

### Web Scraper
- Purpose: Retrieve and extract structured content from web pages for analysis
- Planned features: robots-aware fetching, content extraction, readability, sitemap crawling, rate limiting, retries

### MCP Market Data Providers
- Purpose: Standardize connections to market data sources using MCP (Model Context Protocol) adapters
- Planned providers: equities (quotes, OHLCV, fundamentals), news, analytics
- Benefits: unified schema, interchangeable backends, safer tool execution

## Project Layout

```
FinancialAgentFramework/
  README.md
  snapTrade.py            # SnapTrade tool wrapper + simple CLI demo
  tests/
    testSnapTrade.py      # Unit tests for snapTrade.py (pytest)
```

## Quickstart

### Prerequisites
- Python 3.9+
- PowerShell (Windows) or bash/zsh (macOS/Linux)

### Install dependencies
You can install per-tool as needed:

```powershell
py -m pip install snaptrade-python-sdk python-dotenv pytest
```

### Configure environment
Create a `.env` in the project root (or export in your shell):

```
CLIENTID=your_snaptrade_client_id
SECRET=your_snaptrade_consumer_key
USER_ID=your_user_id
USER_SECRET=your_user_secret
```

Alternatively, use the `SNAPTRADE_*` variants listed above. For a first-time local check without an existing user, omit `USER_ID`/`USER_SECRET` and a test user will be registered.

### Run the SnapTrade tool (demo)

```powershell
py snapTrade.py
```

The script prints a Connection Portal URL. Open it to connect your Fidelity (or other supported) brokerage account. If already connected, it lists Fidelity accounts and prints holdings payload.

## Testing

Run the test suite:

```powershell
py -m pytest -q
```

Run a specific test file/class/method:

```powershell
py -m pytest tests\testSnapTrade.py -q
py -m pytest tests\testSnapTrade.py::TestSnapTrade -q
py -m pytest tests\testSnapTrade.py::TestSnapTrade::test_method_name -q
```

## Security & Compliance
- Store secrets in env vars or a secret manager; never commit them
- Principle of least privilege for API keys
- SnapTrade integration is read-only; verify your use complies with SnapTrade and brokerage policies

## Roadmap
- Agent core: planning, tool selection, guardrails
- Web scraping tool: robust crawler and extractor
- MCP adapters: multiple market data providers, unified schema
- Portfolio analytics: risk metrics, factor exposures, scenario analysis
- Strategy research: screeners, backtests, explainable outputs
- Orchestration: workflows, scheduling, and human-in-the-loop reviews

## Notes
- For SnapTrade details, see the official docs and SDK. Most operations require both a user ID and user secret.