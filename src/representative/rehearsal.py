from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .meeting_ingress import MeetingIngressError


class RehearsalStep(str, Enum):
    BOT_JOINED = "bot_joined"
    DISCLOSURE_DELIVERED = "disclosure_delivered"
    TR_TO_EN_COMPLETED = "tr_to_en_completed"
    EN_TO_TR_COMPLETED = "en_to_tr_completed"
    LOW_CONFIDENCE_SIGNALLED = "low_confidence_signalled"
    BILINGUAL_TRANSCRIPT_WRITTEN = "bilingual_transcript_written"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"
    BOT_LEFT = "bot_left"


CLOSED_REHEARSAL_STEPS = tuple(RehearsalStep)


@dataclass(frozen=True)
class ClosedRehearsal:
    completed: tuple[RehearsalStep, ...] = ()

    @property
    def next_step(self) -> RehearsalStep | None:
        if len(self.completed) == len(CLOSED_REHEARSAL_STEPS):
            return None
        return CLOSED_REHEARSAL_STEPS[len(self.completed)]

    @property
    def is_complete(self) -> bool:
        return self.next_step is None

    def advance(self, step: RehearsalStep) -> ClosedRehearsal:
        if step is not self.next_step:
            raise MeetingIngressError("closed_rehearsal_step_out_of_order")
        return ClosedRehearsal(completed=(*self.completed, step))
