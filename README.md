# Terminal Alarm Clock

An async, terminal-based alarm clock in Python. No GUI. Alarms are stored in a JSON file with atomic writes. Supports recurring schedules (daily, weekdays, or custom days), and snooze/dismiss controls when alarms ring.

## Quick Start

Requires **Python 3.9+** (standard library only — nothing to install).

From the project root (`alarm/`), run:

```bash
python -m alarmclock
```

On some systems use `python3`:

```bash
python3 -m alarmclock
```

You'll drop into an interactive prompt:

```
=== Alarm Clock ===
Type 'help' for available commands.

alarm>
```

The clock watches the time in the background (async, non-blocking) while you type commands. When an alarm's time is reached, it prints an alert and rings the terminal bell (`\a`).

## Commands

| Command   | What it does                                                           |
| --------- | ---------------------------------------------------------------------- |
| `set`     | Set a new alarm — prompts for time (`HH:MM`), optional label, and repeat schedule |
| `list`    | Show all stored alarms with index, id, repeat schedule, and any snooze |
| `delete`  | Delete an alarm by its index or id                                     |
| `snooze`  | Snooze the currently ringing alarm (default 5 minutes)                 |
| `dismiss` | Stop the ringing alarm; or when nothing is ringing, disable an alarm by id |
| `help`    | Show the command list                                                  |
| `exit` / `quit` | Quit cleanly                                                      |

### Example session

```
alarm> set
Enter alarm time (HH:MM): 07:30
Enter alarm label (optional): Wake up
Repeat (once/daily/weekdays/weekends, or days like mon,wed,fri) [once]: weekdays
Alarm set for 07:30 (Wake up) repeat: weekdays

alarm> set
Enter alarm time (HH:MM): 12:00
Enter alarm label (optional): Lunch
Repeat (once/daily/weekdays/weekends, or days like mon,wed,fri) [once]: once
Alarm set for 12:00 (Lunch)

alarm> list
  [0] 07:30 - Wake up [enabled] repeat: weekdays (id: b636db02)
  [1] 12:00 - Lunch [enabled] repeat: once (id: b447d6f4)

alarm> 
*** ALARM: Wake up (07:30) ***
Type 'snooze' to snooze, or 'dismiss' to stop.

alarm> snooze
Snooze minutes [5]: 
Snoozed until 07:35.

alarm> list
  [0] 07:30 - Wake up [enabled] repeat: weekdays (snoozed until 07:35) (id: b636db02)
  [1] 12:00 - Lunch [enabled] repeat: once (id: b447d6f4)

alarm> 
*** ALARM: Wake up (07:30) ***
Type 'snooze' to snooze, or 'dismiss' to stop.

alarm> dismiss
Alarm stopped. (Will recur on next matching weekday.)

alarm> exit
Goodbye!
```

Times are entered in 24-hour format. Invalid input (e.g. `25:99`) is rejected with a clear message and re-prompted.

### Recurring alarms

When setting an alarm, you are prompted for a repeat schedule:

```
Repeat (once/daily/weekdays/weekends, or days like mon,wed,fri) [once]:
```

Accepted repeat values:
- `once` (or blank) — Fires once, then auto-disables.
- `daily` — Fires every day at the set time.
- `weekdays` — Monday through Friday.
- `weekends` — Saturday and Sunday.
- Comma or space-separated day list — E.g., `mon,wed,fri` or `tue thu` for only those weekdays. Use full names (`monday`, `tuesday`, …) or abbreviations (`mon`, `tue`, …).

Recurring alarms remain scheduled and fire on each matching weekday. One-time alarms automatically disable after firing.

### Snooze

When an alarm rings, the terminal displays the alert message and shows:

```
Type 'snooze' to snooze, or 'dismiss' to stop.
```

- **`snooze`** — While the alarm is ringing, you can type this command. It prompts for a snooze duration (blank defaults to 5 minutes) and re-rings the alarm after that time has elapsed.
- **`dismiss`** — Stops the currently ringing alarm. For a recurring alarm, it stays scheduled for its next matching weekday; a one-time alarm stays disabled. When no alarm is ringing, `dismiss` works as before: disables an alarm by id and removes it from the schedule.

## Persistence

Alarms are saved to `alarms.json` in the working directory and reloaded on the next run. Writes are **atomic** (write-to-temp-then-`os.replace`), so the file is never left corrupted even if the program is killed mid-save. A corrupt or missing file is tolerated (treated as "no alarms") rather than crashing.

Each alarm record now includes `repeat` (list of matched weekday codes) and `snooze_until` (optional timestamp for snoozed alarms). Old alarm files without these fields remain compatible and load correctly; missing fields default to `once` and `null` respectively.

## Project Structure

```
alarm/
├── README.md
└── alarmclock/            # the package
    ├── __init__.py        # package metadata
    ├── __main__.py        # entry point — enables `python -m alarmclock`
    ├── models.py          # Alarm data model + time validation
    ├── storage.py         # JSON persistence with atomic writes
    ├── scheduler.py       # async clock watcher + notification/beep
    └── cli.py             # async user interface + command loop
```

- **`models.py`** — `Alarm` dataclass with `repeat` (weekday list) and `snooze_until` (timestamp) fields; `validate_time()`, `new_id()`, and repeat validation.
- **`storage.py`** — `Storage.load()` / `Storage.save()` with atomic temp-file writes; handles `repeat` and `snooze_until` fields (backward compatible).
- **`scheduler.py`** — `Scheduler` runs an `asyncio` loop that fires recurring alarms on matching weekdays and re-fires snoozed alarms; `notify()` prints the alert and beeps.
- **`cli.py`** — `AlarmClockApp` prompts for repeat schedule on `set`, handles `snooze` and `dismiss` during ring, reads input via a thread executor so the scheduler never blocks; wires everything together.

## Requirements

### Functional Requirements

1. **Set an alarm** — Enter a time (`HH:MM`, 24-hour) with an optional label and repeat schedule.
2. **Multiple alarms** — Several alarms can be active at once.
3. **Recurring alarms** — Set alarms to repeat daily, on weekdays/weekends, or on specific custom days.
4. **List alarms** — View all currently stored alarms with repeat schedule and any active snooze.
5. **Delete an alarm** — Remove an alarm before it triggers.
6. **Trigger notification** — Alert the user in the terminal (message + beep) when an alarm time is reached.
7. **Snooze** — Defer a ringing alarm by 5 minutes (or a custom duration).
8. **Dismiss** — Stop a ringing alarm; or disable an alarm by id when nothing is ringing.
9. **Persistence** — Alarms are saved to and loaded from a JSON file across runs.
10. **Input validation** — Reject invalid input with a clear message and re-prompt.
11. **Exit** — Quit cleanly at any time.

### Non-Functional Requirements

1. **Async / non-blocking** — Uses `asyncio`; watching the clock never blocks user input.
2. **JSON storage** — Alarms persisted in a JSON file.
3. **Atomic writes** — Save via write-to-temp-then-replace so the JSON file is never left corrupted or partially written.
4. **Pure Python** — Standard library only, no external dependencies.
5. **Accurate timing** — Alarms trigger within a few seconds of the set time.
6. **Reliability** — Handles bad input and interrupts without crashing.
7. **Portability** — Runs on Windows, macOS, and Linux with a standard Python install.
