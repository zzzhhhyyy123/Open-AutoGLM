"""Adapter for converting alternative model action formats to AutoGLM format.

Converts action strings from UI-TARS style models to the internal AutoGLM
dict format used by ActionHandler. This allows the framework to support
multiple model output formats while reusing the same execution pipeline.

Supported new-format actions:
    click(start_box='<|box_start|>(x,y)<|box_end|>')
    left_double(start_box='<|box_start|>(x,y)<|box_end|>')
    right_single(start_box='<|box_start|>(x,y)<|box_end|>')
    drag(start_box='...', end_box='...')
    hotkey(key='...')
    type(content='...')
    scroll(start_box='...', direction='...')
    wait()
    finished()
    call_user()
"""

import re
from typing import Any

# All action function names recognized in the new format
NEW_FORMAT_ACTIONS = (
    "click",
    "left_double",
    "right_single",
    "drag",
    "hotkey",
    "type",
    "scroll",
    "wait",
    "finished",
    "call_user",
)

# Regex to extract coordinates from <|box_start|>(x,y)<|box_end|>
_BOX_PATTERN = re.compile(
    r"<\|box_start\|>\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*<\|box_end\|>"
)

# Default scroll distance in the 0-999 coordinate space (~30% of screen)
_SCROLL_DISTANCE = 300


def is_new_format(action_str: str) -> bool:
    """Check whether an action string uses the new model format.

    Args:
        action_str: Raw action string from the model.

    Returns:
        True if the string starts with a recognized new-format action name.
    """
    stripped = action_str.strip()
    for name in NEW_FORMAT_ACTIONS:
        if stripped.startswith(name + "(") or stripped == name + "()":
            return True
    return False


def _extract_box_coords(box_str: str) -> list[int]:
    """Extract [x, y] from a ``<|box_start|>(x,y)<|box_end|>`` string."""
    m = _BOX_PATTERN.search(box_str)
    if not m:
        raise ValueError(f"Cannot extract coordinates from: {box_str}")
    return [int(m.group(1)), int(m.group(2))]


def _extract_kwarg(action_str: str, key: str) -> str | None:
    """Extract the string value of a keyword argument from an action call.

    Handles both single-quoted and double-quoted values, including values
    that may contain escaped quotes.
    """
    pattern = re.compile(
        rf"""{key}\s*=\s*(['"])(.*?)\1""",
        re.DOTALL,
    )
    m = pattern.search(action_str)
    return m.group(2) if m else None


def _clamp(value: int, lo: int = 0, hi: int = 999) -> int:
    return max(lo, min(hi, value))


def convert(action_str: str) -> dict[str, Any]:
    """Convert a new-format action string to an AutoGLM-compatible dict.

    The returned dict has the same structure as what ``parse_action`` in
    ``handler.py`` produces for the original ``do(...)``/``finish(...)`` format:
    ``{"_metadata": "do"|"finish", "action": "...", ...}``.

    Args:
        action_str: Raw new-format action string.

    Returns:
        Action dictionary ready for ``ActionHandler.execute()``.

    Raises:
        ValueError: If the action string cannot be parsed.
    """
    s = action_str.strip()

    # --- click ---
    if s.startswith("click("):
        coords = _extract_box_coords(s)
        return {"_metadata": "do", "action": "Tap", "element": coords}

    # --- left_double ---
    if s.startswith("left_double("):
        coords = _extract_box_coords(s)
        return {"_metadata": "do", "action": "Double Tap", "element": coords}

    # --- right_single  →  Long Press (closest mobile equivalent of right-click) ---
    if s.startswith("right_single("):
        coords = _extract_box_coords(s)
        return {"_metadata": "do", "action": "Long Press", "element": coords}

    # --- drag ---
    if s.startswith("drag("):
        start_str = _extract_kwarg(s, "start_box")
        end_str = _extract_kwarg(s, "end_box")
        if not start_str or not end_str:
            raise ValueError(f"drag() missing start_box or end_box: {s}")
        start = _extract_box_coords(start_str)
        end = _extract_box_coords(end_str)
        return {"_metadata": "do", "action": "Swipe", "start": start, "end": end}

    # --- hotkey ---
    if s.startswith("hotkey("):
        key = _extract_kwarg(s, "key") or ""
        return _convert_hotkey(key)

    # --- type ---
    if s.startswith("type("):
        content = _extract_kwarg(s, "content")
        if content is None:
            content = ""
        submit = False
        if content.endswith("\\n"):
            content = content[:-2]
            submit = True
        return {
            "_metadata": "do",
            "action": "Type",
            "text": content,
            "submit": submit,
        }

    # --- scroll ---
    if s.startswith("scroll("):
        coords = _extract_box_coords(s)
        direction = (_extract_kwarg(s, "direction") or "down").lower().strip()
        start, end = _compute_scroll_endpoints(coords, direction)
        return {"_metadata": "do", "action": "Swipe", "start": start, "end": end}

    # --- wait ---
    if s.startswith("wait("):
        return {"_metadata": "do", "action": "Wait", "duration": "5 seconds"}

    # --- finished ---
    if s.startswith("finished("):
        return {"_metadata": "finish", "message": "Task completed"}

    # --- call_user ---
    if s.startswith("call_user("):
        return {
            "_metadata": "do",
            "action": "Take_over",
            "message": "User assistance needed",
        }

    raise ValueError(f"Unrecognized new-format action: {s}")


def _convert_hotkey(key: str) -> dict[str, Any]:
    """Map a hotkey name to an AutoGLM action dict."""
    normalized = key.strip().lower()

    # Navigation keys map directly to existing actions
    if normalized in ("escape", "back"):
        return {"_metadata": "do", "action": "Back"}
    if normalized == "home":
        return {"_metadata": "do", "action": "Home"}

    # Keys that require sending an Android keyevent
    keycode_map = {
        "enter": "66",
        "return": "66",
        "backspace": "67",
        "delete": "67",
        "del": "112",
        "tab": "61",
        "space": "62",
        "volume_up": "24",
        "volume_down": "25",
        "power": "26",
        "menu": "82",
    }

    if normalized in keycode_map:
        return {
            "_metadata": "do",
            "action": "KeyEvent",
            "keycode": keycode_map[normalized],
        }

    # Fallback: treat the raw key value as an Android keycode string
    return {"_metadata": "do", "action": "KeyEvent", "keycode": key}


def _compute_scroll_endpoints(
    origin: list[int], direction: str
) -> tuple[list[int], list[int]]:
    """Compute swipe start/end from a scroll origin and direction.

    The mapping follows standard mobile scroll semantics:
    - ``down``  → finger swipes upward  (view content below)
    - ``up``    → finger swipes downward (view content above)
    - ``left``  → finger swipes rightward
    - ``right`` → finger swipes leftward
    """
    x, y = origin
    d = _SCROLL_DISTANCE

    if direction == "down":
        return [x, _clamp(y + d)], [x, _clamp(y - d)]
    elif direction == "up":
        return [x, _clamp(y - d)], [x, _clamp(y + d)]
    elif direction == "left":
        return [_clamp(x + d), y], [_clamp(x - d), y]
    elif direction == "right":
        return [_clamp(x - d), y], [_clamp(x + d), y]
    else:
        # Default to scroll down
        return [x, _clamp(y + d)], [x, _clamp(y - d)]
