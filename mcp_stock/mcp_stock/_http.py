"""Patch requests to respect TRUST_SYSTEM_PROXY config before any AKShare imports."""

from mcp_stock.config import TRUST_SYSTEM_PROXY

if not TRUST_SYSTEM_PROXY:
    import requests as _requests

    _original_session_init = _requests.Session.__init__

    def _patched_init(self, *args, **kwargs):
        _original_session_init(self, *args, **kwargs)
        self.trust_env = False

    _requests.Session.__init__ = _patched_init
