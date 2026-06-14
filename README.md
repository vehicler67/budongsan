# Hermes Hybrid Model Setup (World-First Discovery)

> Status: verified on 2026-06-14.
> Target reader: Hermes Desktop users who want per-session model routing without editing `config.yaml`.

## TL;DR
In Hermes Desktop, the **default model is shared by every session** unless you explicitly tell the current session to use a different model. The trick that makes this behave like a “hybrid” setup is the **Persist globally** checkbox inside `/model`.

## The limitation
Hermes does **not** have an automatic hybrid router. There is no “light work uses X, heavy work uses Y” mode built into the product right now.

The observable behavior is:
- `config.yaml` holds one `model.default`.
- The active session can temporarily override it.
- Telegram and system services still follow the stored default unless overridden separately.

## The working pattern: hybrid users have to route manually
If you want hybrid behavior now, you either:
- keep switching models manually, or
- rely on **failover only after the primary model errors out**.

There is **no verified feature** in Hermes that automatically chooses “stepfun for desktop, deepseek for Telegram” without explicit user action.

## What I actually found useful
- Real-time usage/balance monitoring is better than guessing.
- Provider status should be checked before changing the default.
- Documenting the failure path helps more than documenting the happy path.

## Official references
- Configuration: https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- Tools: https://hermes-agent.nousresearch.com/docs/user-guide/features/tools
- Architecture: https://hermes-agent.nousresearch.com/docs/developer-guide/architecture
- Model catalog: https://hermes-agent.nousresearch.com/docs/api/model-catalog.json

## Concrete recommendation
Until Hermes ships an explicit hybrid/routing mode, the safest setup is:
1. use one stable default in `config.yaml`,
2. override per session only when needed,
3. add failover providers so failures degrade gracefully instead of failing silently.

If Hermes later adds documented platform-specific default model settings, that should replace this manual pattern.
