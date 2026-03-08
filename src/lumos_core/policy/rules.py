from lumos_core.context.context import Context
from lumos_core.policy.decision import Decision


class PolicyRules:
    @staticmethod
    def evaluate(ctx: Context, mode: str, confidence_threshold: float, engine) -> Decision:
        if mode == "offline" or not ctx.online:
            payload = engine.process(getattr(ctx, "message", ""))
            return Decision(True, "Offline mod: offline engine", payload)

        # ONLINE SECURITY GATE
        if mode != "offline" and ctx.online:
            if not getattr(ctx, "unlocked", False):
                return Decision(True, "Locked", {"response": "LOCKED", "reason": "", "follow_up": "kilit"})
            if not (getattr(ctx, "lumos_id", "") or "").strip():
                return Decision(True, "No identity", {"response": "Kimlik yok", "reason": "", "follow_up": "python -m lumos_core.scripts.init_identity"})


        if not getattr(ctx, "lumos_id", ""):
            return Decision(
                False,
                "Kimlik yok",
                {
                    "response": "Online moda geçemem. Önce kimlik kurulmalı.",
                    "reason": "Cihaz kimliği (identity) bulunamadı.",
                    "follow_up": "Terminal: python -m lumos_core.scripts.init_identity"
                }
            )

        if ctx.confidence < confidence_threshold:
            return Decision(False, "Emin değil", None)

        if ctx.user_is_child:
            return Decision(True, "Çocuk modu", {"response": "Lumos burada. (Çocuk modu)", "reason": "", "follow_up": ""})

        msg = getattr(ctx, "message", "")
        short_ctx = getattr(ctx, "short_context", "")

        try:
            payload = engine.process(msg, short_ctx)
        except TypeError:
            payload = engine.process(msg)

        return Decision(True, "Online mod: engine", payload)
