"""
Lightweight response_builder: runs after the provider response.
Applies user address preferences (fixed vs adaptive) without changing architecture.
"""
from __future__ import annotations

from lumos_core.user_identity import UserIdentity


def build_response(response_text: str, user: UserIdentity | None) -> str:
    """
    Optionally prefix or adapt the provider response using user address preferences.
    - fixed + preferred_address: prefix with address (Lumos always uses preferred_address).
    - adaptive or no preferred_address: return response as-is (natural, avoid overly informal).
    """
    if not user:
        return response_text
    if user.address_mode == "fixed" and (user.preferred_address or "").strip():
        return f"{user.preferred_address.strip()},\n\n{response_text}"
    # adaptive: return unchanged; caller may later add light formalization
    return response_text
