from __future__ import annotations

import json
import os
import tempfile
from .models import Alarm


class Storage:
    """Manages persistent storage of alarm configurations using atomic file operations."""

    def __init__(self, path: str = "alarms.json") -> None:
        """
        Initialize the Storage instance.

        Args:
            path: Path to the JSON file for storing alarms. Defaults to "alarms.json".
        """
        self.path = str(path)

    def load(self) -> list[Alarm]:
        """
        Load alarms from the storage file.

        Returns a list of Alarm objects deserialized from JSON. If the file does not
        exist, is empty, or is corrupt, returns an empty list without raising exceptions.

        Returns:
            A list of Alarm objects, or an empty list if no valid alarms are found.
        """
        if not os.path.exists(self.path):
            return []

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                content = f.read()

            # Handle empty files
            if not content.strip():
                return []

            data = json.loads(content)

            # Ensure data is a list
            if not isinstance(data, list):
                return []

            # Convert each alarm dict to an Alarm object
            alarms = []
            for alarm_dict in data:
                try:
                    alarm = Alarm.from_dict(alarm_dict)
                    alarms.append(alarm)
                except (ValueError, KeyError, TypeError):
                    # Skip invalid alarm entries, continue with others
                    continue

            return alarms

        except (json.JSONDecodeError, OSError, ValueError, KeyError, TypeError):
            # Return empty list on any error to prevent crashes
            return []

    def save(self, alarms: list[Alarm]) -> None:
        """
        Atomically save alarms to the storage file.

        Uses a temporary file in the same directory as the target file, then atomically
        replaces the target file to ensure data integrity even if the process is interrupted.

        Args:
            alarms: A list of Alarm objects to persist.

        Raises:
            OSError: If the atomic write operation fails after cleanup.
        """
        # Serialize alarms to JSON
        data = [a.to_dict() for a in alarms]
        json_content = json.dumps(data, indent=2)
        json_bytes = json_content.encode("utf-8")

        # Determine the directory for the temp file (same directory as target)
        target_dir = os.path.dirname(self.path)
        if not target_dir:
            target_dir = "."

        # Create a temporary file in the same directory
        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(dir=target_dir)

            # Write JSON content to temp file
            os.write(fd, json_bytes)

            # Ensure data is flushed and synced to disk
            os.fsync(fd)
            os.close(fd)
            fd = None

            # Atomically replace the target file
            os.replace(tmp_path, self.path)

        except Exception:
            # Clean up temp file if it exists
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass

            if tmp_path is not None:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

            # Re-raise the original exception
            raise
