from __future__ import annotations

import asyncio
import sys
import time
from typing import Callable

from .models import Alarm, DAYS


def notify(alarm: Alarm) -> None:
    """
    Emit a prominent audible and visual alert for the given alarm.

    Args:
        alarm: The Alarm object to notify about.
    """
    # Print a clear, prominent multi-line alert
    print("=" * 60)
    current_time = time.strftime("%H:%M", time.localtime())
    alert_msg = f"ALARM! {current_time}"
    if alarm.label:
        alert_msg += f" - {alarm.label}"
    print(alert_msg)
    print("=" * 60)

    # Emit terminal beep
    sys.stdout.write("\a")
    sys.stdout.flush()


class Scheduler:
    """
    An async scheduler that monitors alarms and triggers them at the appropriate time.
    """

    def __init__(
        self,
        get_alarms: Callable[[], list[Alarm]],
        on_trigger: Callable[[Alarm], None]
    ) -> None:
        """
        Initialize the Scheduler.

        Args:
            get_alarms: Callable that returns the current list of alarms.
            on_trigger: Callable to invoke when an alarm should trigger.
        """
        self.get_alarms = get_alarms
        self.on_trigger = on_trigger
        self._fired: set[str] = set()

    async def run(self) -> None:
        """
        Run the scheduler loop indefinitely.

        Monitors alarms and triggers them when their scheduled time is reached or snooze expires.
        Handles cancellation gracefully and continues on transient errors.
        """
        while True:
            try:
                # Get current time components
                now = time.localtime()
                current_hhmm = time.strftime("%H:%M", now)
                today_code = DAYS[now.tm_wday]
                epoch = time.time()

                # Check each alarm
                for alarm in self.get_alarms():
                    if not alarm.enabled:
                        continue

                    # (A) Check for snooze fire: if snooze has expired
                    if alarm.snooze_until is not None and epoch >= alarm.snooze_until:
                        # Clear snooze first to prevent re-firing each second
                        alarm.snooze_until = None
                        self.on_trigger(alarm)
                        continue

                    # (B) Check for scheduled fire:
                    # Fire if time matches AND (one-time alarm OR recurring on this day)
                    if alarm.time == current_hhmm and (not alarm.repeat or today_code in alarm.repeat):
                        # Create a unique key for this alarm at this minute
                        key = f"{alarm.id}:{current_hhmm}"

                        # Trigger the alarm if we haven't already this minute
                        if key not in self._fired:
                            self._fired.add(key)
                            self.on_trigger(alarm)

                # Prune old keys that are no longer relevant.
                # Keep only keys ending with the current HH:MM so alarms can
                # fire again on a future day/minute.
                self._fired = {k for k in self._fired if k.endswith(current_hhmm)}

                # Sleep for 1 second before checking again
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                # Handle cancellation cleanly
                break
            except Exception as e:
                # Swallow other exceptions and print warning
                print(f"Warning: Scheduler error: {e}", file=sys.stderr)
                await asyncio.sleep(1)
