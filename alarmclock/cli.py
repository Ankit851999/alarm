from __future__ import annotations

import asyncio
import time
from .models import Alarm, validate_time, new_id, validate_repeat, describe_repeat
from .storage import Storage
from .scheduler import Scheduler, notify


class AlarmClockApp:
    """Terminal-based alarm clock application."""

    def __init__(self, storage: Storage):
        """Initialize the app with a storage backend."""
        self.storage = storage
        self.alarms = storage.load()
        self._running = True
        self._ringing: set[str] = set()  # ids of alarms currently ringing

    def _persist(self) -> None:
        """Save alarms to storage."""
        self.storage.save(self.alarms)

    async def _ainput(self, prompt: str) -> str:
        """Read input without blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)

    async def _cmd_set(self) -> None:
        """Set a new alarm: prompt for time, label, and repeat schedule."""
        while True:
            try:
                time_str = await self._ainput("Enter alarm time (HH:MM): ")
                alarm_time = validate_time(time_str)
                break
            except ValueError as e:
                print(f"Error: {e}")

        label = await self._ainput("Enter alarm label (optional): ")
        label = label.strip() if label else ""

        while True:
            try:
                repeat_str = await self._ainput("Repeat (once/daily/weekdays/weekends, or days like mon,wed,fri) [once]: ")
                repeat = validate_repeat(repeat_str)
                break
            except ValueError as e:
                print(f"Error: {e}")

        alarm = Alarm(new_id(), alarm_time, label, repeat=repeat)
        self.alarms.append(alarm)
        self._persist()
        print(f"Alarm set for {alarm_time} ({describe_repeat(repeat)})" + (f" - {label}" if label else ""))

    async def _cmd_list(self) -> None:
        """List all alarms with repeat schedule and snooze status."""
        if not self.alarms:
            print("No alarms set.")
            return

        for i, alarm in enumerate(self.alarms):
            status = "enabled" if alarm.enabled else "disabled"
            label_str = f" - {alarm.label}" if alarm.label else ""
            repeat_str = f"repeat: {describe_repeat(alarm.repeat)}"
            line = f"  [{i}] {alarm.time}{label_str} [{status}] {repeat_str} (id: {alarm.id})"
            if alarm.snooze_until is not None:
                snooze_time = time.strftime("%H:%M", time.localtime(alarm.snooze_until))
                line += f" (snoozed until {snooze_time})"
            print(line)

    async def _cmd_delete(self) -> None:
        """Delete an alarm by index or id."""
        if not self.alarms:
            print("No alarms to delete.")
            return

        await self._cmd_list()
        identifier = await self._ainput("Enter alarm index or id to delete: ")

        # Try as index first
        try:
            index = int(identifier)
            if 0 <= index < len(self.alarms):
                self.alarms.pop(index)
                self._persist()
                print("Alarm deleted.")
                return
        except (ValueError, IndexError):
            pass

        # Try as id
        for i, alarm in enumerate(self.alarms):
            if alarm.id == identifier:
                self.alarms.pop(i)
                self._persist()
                print("Alarm deleted.")
                return

        print("Alarm not found.")

    def _on_trigger(self, alarm: Alarm) -> None:
        """Handle alarm trigger: notify, track as ringing, auto-disable one-time alarms."""
        notify(alarm)
        self._ringing.add(alarm.id)
        print("Type 'snooze' to snooze, or 'dismiss' to stop.")
        # One-time alarms auto-disable so they don't fire again; recurring alarms stay scheduled.
        if not alarm.repeat:
            alarm.enabled = False
        self._persist()

    async def _cmd_snooze(self) -> None:
        """Snooze the currently ringing alarm(s) for a specified number of minutes."""
        if not self._ringing:
            print("No alarm is currently ringing.")
            return

        snooze_str = await self._ainput("Snooze minutes [5]: ")
        if snooze_str.strip() == "":
            minutes = 5
        else:
            try:
                minutes = int(snooze_str)
                if minutes <= 0:
                    print("Error: Snooze duration must be positive.")
                    return
            except ValueError:
                print("Error: Invalid snooze duration.")
                return

        when = time.time() + minutes * 60
        for alarm_id in self._ringing:
            for alarm in self.alarms:
                if alarm.id == alarm_id:
                    alarm.enabled = True  # Re-enable in case it was a one-time alarm
                    alarm.snooze_until = when
                    break

        self._ringing.clear()
        self._persist()
        snooze_time_str = time.strftime("%H:%M", time.localtime(when))
        print(f"Snoozed for {minutes} min (until {snooze_time_str}).")

    async def _cmd_dismiss(self) -> None:
        """Dismiss ringing alarm(s), or disable a scheduled alarm by id."""
        # If an alarm is currently ringing, dismiss it (stop the ringing without disabling)
        if self._ringing:
            for alarm_id in self._ringing:
                for alarm in self.alarms:
                    if alarm.id == alarm_id:
                        alarm.snooze_until = None  # Cancel any pending snooze
                        break
            self._ringing.clear()
            self._persist()
            print("Alarm dismissed.")
            return

        # Otherwise, show list and prompt to disable a scheduled alarm
        if not self.alarms:
            print("No alarms to dismiss.")
            return

        await self._cmd_list()
        alarm_id = await self._ainput("Enter alarm id to dismiss: ")

        for alarm in self.alarms:
            if alarm.id == alarm_id:
                alarm.enabled = False
                self._persist()
                print(f"Alarm {alarm_id} dismissed.")
                return

        print("Alarm not found.")

    async def _cmd_help(self) -> None:
        """Print help information."""
        help_text = """
Available commands:
  set      - Set a new alarm (time, label, and repeat schedule)
  list     - Show all alarms
  delete   - Delete an alarm by index or id
  snooze   - Snooze the currently ringing alarm
  dismiss  - Stop the ringing alarm, or disable an alarm by id
  help     - Show this help message
  exit / quit - Exit the application
"""
        print(help_text)

    async def run(self) -> None:
        """Main application loop."""
        print("\n=== Alarm Clock ===")
        print("Type 'help' for available commands.\n")

        # Start the scheduler as a background task
        scheduler = Scheduler(lambda: self.alarms, self._on_trigger)
        scheduler_task = asyncio.create_task(scheduler.run())

        try:
            while self._running:
                try:
                    cmd = await self._ainput("alarm> ")
                    cmd = cmd.strip().lower()

                    if cmd in ("exit", "quit"):
                        self._running = False
                    elif cmd == "set":
                        await self._cmd_set()
                    elif cmd == "list":
                        await self._cmd_list()
                    elif cmd == "delete":
                        await self._cmd_delete()
                    elif cmd == "snooze":
                        await self._cmd_snooze()
                    elif cmd == "dismiss":
                        await self._cmd_dismiss()
                    elif cmd == "help":
                        await self._cmd_help()
                    elif cmd:
                        print(f"Unknown command: {cmd}. Type 'help' for options.")
                except EOFError:
                    self._running = False
                except KeyboardInterrupt:
                    self._running = False

        finally:
            # Cancel and clean up the scheduler task
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
            print("\nGoodbye!")


async def main() -> None:
    """Entry point for the application."""
    app = AlarmClockApp(Storage("alarms.json"))
    await app.run()
