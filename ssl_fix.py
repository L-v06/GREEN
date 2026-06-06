# ssl_fix.py
"""
SSL compatibility patch for Python 3.14 on Windows.

Python 3.14 changed the default SSL minimum version to an unset state (-2)
which causes aiohttp (used by discord.py) to fail the TLS handshake with
Discord's servers on some Windows configurations.

This module must be imported at the VERY TOP of main.py, before discord
or aiohttp are imported.

Usage in main.py:
    import ssl_fix   # ← first line, before everything else
    import discord
    ...
"""

import ssl
import aiohttp


def _build_ssl_context() -> ssl.SSLContext:
    """
    Creates an SSL context that explicitly allows TLS 1.2 and 1.3,
    bypassing the broken default negotiation in Python 3.14 on Windows.
    """
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    return ctx


# Patch aiohttp's default connector to always use our context.
# This affects every outgoing HTTPS connection made by aiohttp,
# including all Discord API calls and gateway connections.
_SSL_CONTEXT = _build_ssl_context()
_original_init = aiohttp.TCPConnector.__init__


def _patched_connector_init(self, *args, **kwargs):
    # Only inject ssl if the caller didn't provide one explicitly
    kwargs.setdefault("ssl", _SSL_CONTEXT)
    _original_init(self, *args, **kwargs)


aiohttp.TCPConnector.__init__ = _patched_connector_init

print("✅ ssl_fix: SSL context patched (TLS 1.2–1.3, Python 3.14 Windows workaround)")