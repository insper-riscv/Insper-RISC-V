# Live C example

The original PR example is preserved in `c/live/src.c`. Open this folder as an external SDK application. Register this checkout with `scripts/install-user.sh`, install `share/rv32-development.vsix`, and reopen this folder in its Dev Container. The three editor buttons use the current SDK.

The old embedded `Live/config.yaml`, `scripts/live_c.py` and root container/tasks were replaced by the maintained application SDK. This example uses the same `rv32.toml` interface as newly created projects. See [SDK.md](../SDK.md). No Tests or TopLevel submodule is required.
