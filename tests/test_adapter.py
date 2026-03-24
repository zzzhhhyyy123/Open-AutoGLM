"""Tests for phone_agent.actions.adapter — new model format conversion."""

import pytest

from phone_agent.actions.adapter import (
    _clamp,
    _convert_hotkey,
    _extract_box_coords,
    _extract_kwarg,
    convert,
    is_new_format,
)


# ---------------------------------------------------------------------------
# is_new_format
# ---------------------------------------------------------------------------
class TestIsNewFormat:
    def test_click(self):
        assert is_new_format("click(start_box='<|box_start|>(500,300)<|box_end|>')")

    def test_left_double(self):
        assert is_new_format(
            "left_double(start_box='<|box_start|>(100,200)<|box_end|>')"
        )

    def test_right_single(self):
        assert is_new_format("right_single(start_box='<|box_start|>(0,0)<|box_end|>')")

    def test_drag(self):
        assert is_new_format(
            "drag(start_box='<|box_start|>(1,2)<|box_end|>', end_box='<|box_start|>(3,4)<|box_end|>')"
        )

    def test_hotkey(self):
        assert is_new_format("hotkey(key='Enter')")

    def test_type(self):
        assert is_new_format("type(content='hello')")

    def test_scroll(self):
        assert is_new_format(
            "scroll(start_box='<|box_start|>(500,500)<|box_end|>', direction='down')"
        )

    def test_wait(self):
        assert is_new_format("wait()")

    def test_finished(self):
        assert is_new_format("finished()")

    def test_call_user(self):
        assert is_new_format("call_user()")

    def test_autoglm_format_not_detected(self):
        assert not is_new_format('do(action="Tap", element=[500, 300])')
        assert not is_new_format('finish(message="done")')

    def test_random_string(self):
        assert not is_new_format("hello world")
        assert not is_new_format("")

    def test_leading_whitespace(self):
        assert is_new_format("  click(start_box='<|box_start|>(1,1)<|box_end|>')")


# ---------------------------------------------------------------------------
# _extract_box_coords
# ---------------------------------------------------------------------------
class TestExtractBoxCoords:
    def test_basic(self):
        assert _extract_box_coords("<|box_start|>(123,456)<|box_end|>") == [123, 456]

    def test_with_spaces(self):
        assert _extract_box_coords("<|box_start|>( 10 , 20 )<|box_end|>") == [10, 20]

    def test_zeros(self):
        assert _extract_box_coords("<|box_start|>(0,0)<|box_end|>") == [0, 0]

    def test_max_coords(self):
        assert _extract_box_coords("<|box_start|>(999,999)<|box_end|>") == [999, 999]

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _extract_box_coords("no coords here")


# ---------------------------------------------------------------------------
# _extract_kwarg
# ---------------------------------------------------------------------------
class TestExtractKwarg:
    def test_single_quotes(self):
        assert _extract_kwarg("hotkey(key='Enter')", "key") == "Enter"

    def test_double_quotes(self):
        assert _extract_kwarg('type(content="hello")', "content") == "hello"

    def test_missing_key(self):
        assert _extract_kwarg("hotkey(key='Enter')", "missing") is None

    def test_box_value(self):
        s = "click(start_box='<|box_start|>(5,10)<|box_end|>')"
        assert _extract_kwarg(s, "start_box") == "<|box_start|>(5,10)<|box_end|>"

    def test_content_with_backslash_n(self):
        s = r"type(content='hello world\n')"
        assert _extract_kwarg(s, "content") == r"hello world\n"


# ---------------------------------------------------------------------------
# convert — click
# ---------------------------------------------------------------------------
class TestConvertClick:
    def test_basic(self):
        result = convert("click(start_box='<|box_start|>(500,300)<|box_end|>')")
        assert result == {"_metadata": "do", "action": "Tap", "element": [500, 300]}

    def test_zero_coords(self):
        result = convert("click(start_box='<|box_start|>(0,0)<|box_end|>')")
        assert result["element"] == [0, 0]

    def test_max_coords(self):
        result = convert("click(start_box='<|box_start|>(999,999)<|box_end|>')")
        assert result["element"] == [999, 999]


# ---------------------------------------------------------------------------
# convert — left_double
# ---------------------------------------------------------------------------
class TestConvertLeftDouble:
    def test_basic(self):
        result = convert("left_double(start_box='<|box_start|>(100,200)<|box_end|>')")
        assert result == {
            "_metadata": "do",
            "action": "Double Tap",
            "element": [100, 200],
        }


# ---------------------------------------------------------------------------
# convert — right_single
# ---------------------------------------------------------------------------
class TestConvertRightSingle:
    def test_basic(self):
        result = convert("right_single(start_box='<|box_start|>(300,400)<|box_end|>')")
        assert result == {
            "_metadata": "do",
            "action": "Long Press",
            "element": [300, 400],
        }


# ---------------------------------------------------------------------------
# convert — drag
# ---------------------------------------------------------------------------
class TestConvertDrag:
    def test_basic(self):
        raw = (
            "drag(start_box='<|box_start|>(100,200)<|box_end|>', "
            "end_box='<|box_start|>(300,400)<|box_end|>')"
        )
        result = convert(raw)
        assert result == {
            "_metadata": "do",
            "action": "Swipe",
            "start": [100, 200],
            "end": [300, 400],
        }

    def test_missing_end_box_raises(self):
        with pytest.raises(ValueError):
            convert("drag(start_box='<|box_start|>(1,2)<|box_end|>')")


# ---------------------------------------------------------------------------
# convert — hotkey
# ---------------------------------------------------------------------------
class TestConvertHotkey:
    def test_escape(self):
        result = convert("hotkey(key='Escape')")
        assert result == {"_metadata": "do", "action": "Back"}

    def test_back(self):
        result = convert("hotkey(key='Back')")
        assert result == {"_metadata": "do", "action": "Back"}

    def test_home(self):
        result = convert("hotkey(key='Home')")
        assert result == {"_metadata": "do", "action": "Home"}

    def test_enter(self):
        result = convert("hotkey(key='Enter')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "66"}

    def test_return(self):
        result = convert("hotkey(key='Return')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "66"}

    def test_backspace(self):
        result = convert("hotkey(key='Backspace')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "67"}

    def test_delete(self):
        result = convert("hotkey(key='Delete')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "67"}

    def test_del(self):
        result = convert("hotkey(key='Del')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "112"}

    def test_tab(self):
        result = convert("hotkey(key='Tab')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "61"}

    def test_space(self):
        result = convert("hotkey(key='space')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "62"}

    def test_unknown_key_passthrough(self):
        result = convert("hotkey(key='F5')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "F5"}


# ---------------------------------------------------------------------------
# convert — type
# ---------------------------------------------------------------------------
class TestConvertType:
    def test_basic(self):
        result = convert("type(content='hello world')")
        assert result == {
            "_metadata": "do",
            "action": "Type",
            "text": "hello world",
            "submit": False,
        }

    def test_submit_with_newline(self):
        result = convert(r"type(content='search query\n')")
        assert result == {
            "_metadata": "do",
            "action": "Type",
            "text": "search query",
            "submit": True,
        }

    def test_empty_content(self):
        result = convert("type(content='')")
        assert result["text"] == ""
        assert result["submit"] is False

    def test_submit_only_newline(self):
        result = convert(r"type(content='\n')")
        assert result["text"] == ""
        assert result["submit"] is True


# ---------------------------------------------------------------------------
# convert — scroll
# ---------------------------------------------------------------------------
class TestConvertScroll:
    def test_scroll_down(self):
        result = convert(
            "scroll(start_box='<|box_start|>(500,500)<|box_end|>', direction='down')"
        )
        assert result["_metadata"] == "do"
        assert result["action"] == "Swipe"
        assert result["start"] == [500, 800]
        assert result["end"] == [500, 200]

    def test_scroll_up(self):
        result = convert(
            "scroll(start_box='<|box_start|>(500,500)<|box_end|>', direction='up')"
        )
        assert result["start"] == [500, 200]
        assert result["end"] == [500, 800]

    def test_scroll_left(self):
        result = convert(
            "scroll(start_box='<|box_start|>(500,500)<|box_end|>', direction='left')"
        )
        assert result["start"] == [800, 500]
        assert result["end"] == [200, 500]

    def test_scroll_right(self):
        result = convert(
            "scroll(start_box='<|box_start|>(500,500)<|box_end|>', direction='right')"
        )
        assert result["start"] == [200, 500]
        assert result["end"] == [800, 500]

    def test_scroll_clamps_at_boundary(self):
        result = convert(
            "scroll(start_box='<|box_start|>(100,100)<|box_end|>', direction='up')"
        )
        # up: start_y = 100 - 300 = -200 → clamp to 0
        assert result["start"][1] == 0
        assert result["end"][1] == 400


# ---------------------------------------------------------------------------
# convert — wait
# ---------------------------------------------------------------------------
class TestConvertWait:
    def test_basic(self):
        result = convert("wait()")
        assert result == {"_metadata": "do", "action": "Wait", "duration": "5 seconds"}


# ---------------------------------------------------------------------------
# convert — finished
# ---------------------------------------------------------------------------
class TestConvertFinished:
    def test_basic(self):
        result = convert("finished()")
        assert result == {"_metadata": "finish", "message": "Task completed"}


# ---------------------------------------------------------------------------
# convert — call_user
# ---------------------------------------------------------------------------
class TestConvertCallUser:
    def test_basic(self):
        result = convert("call_user()")
        assert result == {
            "_metadata": "do",
            "action": "Take_over",
            "message": "User assistance needed",
        }


# ---------------------------------------------------------------------------
# convert — error cases
# ---------------------------------------------------------------------------
class TestConvertErrors:
    def test_unknown_action_raises(self):
        with pytest.raises(ValueError, match="Unrecognized"):
            convert("unknown_action()")


# ---------------------------------------------------------------------------
# _clamp
# ---------------------------------------------------------------------------
class TestClamp:
    def test_within_range(self):
        assert _clamp(500) == 500

    def test_below_min(self):
        assert _clamp(-100) == 0

    def test_above_max(self):
        assert _clamp(1500) == 999


# ---------------------------------------------------------------------------
# _convert_hotkey
# ---------------------------------------------------------------------------
class TestConvertHotkeyDirect:
    def test_case_insensitive(self):
        assert _convert_hotkey("ESCAPE") == {"_metadata": "do", "action": "Back"}
        assert _convert_hotkey("escape") == {"_metadata": "do", "action": "Back"}
        assert _convert_hotkey("Escape") == {"_metadata": "do", "action": "Back"}


# ---------------------------------------------------------------------------
# Integration: parse_action dispatches to adapter for new format
# ---------------------------------------------------------------------------
class TestParseActionIntegration:
    """Verify that parse_action in handler.py delegates to adapter for new-format strings."""

    def test_click_through_parse_action(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action("click(start_box='<|box_start|>(250,750)<|box_end|>')")
        assert result == {"_metadata": "do", "action": "Tap", "element": [250, 750]}

    def test_finished_through_parse_action(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action("finished()")
        assert result == {"_metadata": "finish", "message": "Task completed"}

    def test_autoglm_still_works(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action('do(action="Back")')
        assert result == {"_metadata": "do", "action": "Back"}

    def test_autoglm_tap_still_works(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action('do(action="Tap", element=[500, 300])')
        assert result == {"_metadata": "do", "action": "Tap", "element": [500, 300]}

    def test_autoglm_finish_still_works(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action('finish(message="all done")')
        assert result == {"_metadata": "finish", "message": "all done"}

    def test_scroll_through_parse_action(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action(
            "scroll(start_box='<|box_start|>(500,500)<|box_end|>', direction='down')"
        )
        assert result["action"] == "Swipe"

    def test_type_submit_through_parse_action(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action(r"type(content='test\n')")
        assert result["action"] == "Type"
        assert result["text"] == "test"
        assert result["submit"] is True

    def test_hotkey_enter_through_parse_action(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action("hotkey(key='Enter')")
        assert result == {"_metadata": "do", "action": "KeyEvent", "keycode": "66"}

    def test_wait_through_parse_action(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action("wait()")
        assert result == {"_metadata": "do", "action": "Wait", "duration": "5 seconds"}

    def test_call_user_through_parse_action(self):
        from phone_agent.actions.handler import parse_action

        result = parse_action("call_user()")
        assert result["action"] == "Take_over"


# ---------------------------------------------------------------------------
# _parse_response in ModelClient detects new format
# ---------------------------------------------------------------------------
class TestModelClientParseResponse:
    """Verify that ModelClient._parse_response splits thinking/action for new format."""

    def _parse(self, content: str) -> tuple[str, str]:
        from phone_agent.model.client import ModelClient

        client = ModelClient.__new__(ModelClient)
        return client._parse_response(content)

    def test_click_with_thinking(self):
        content = "I need to tap the button.\nclick(start_box='<|box_start|>(500,300)<|box_end|>')"
        thinking, action = self._parse(content)
        assert "I need to tap" in thinking
        assert action.startswith("click(")

    def test_finished_detected(self):
        content = "The task is done.\nfinished()"
        thinking, action = self._parse(content)
        assert "task is done" in thinking
        assert action == "finished()"

    def test_type_detected(self):
        content = "Typing text now.\ntype(content='hello')"
        thinking, action = self._parse(content)
        assert "Typing text" in thinking
        assert action.startswith("type(")

    def test_autoglm_still_detected(self):
        content = 'Thinking...\ndo(action="Tap", element=[100, 200])'
        thinking, action = self._parse(content)
        assert action.startswith("do(action=")

    def test_scroll_detected(self):
        content = "Need to scroll.\nscroll(start_box='<|box_start|>(500,500)<|box_end|>', direction='down')"
        thinking, action = self._parse(content)
        assert action.startswith("scroll(")

    def test_wait_detected(self):
        content = "Waiting...\nwait()"
        thinking, action = self._parse(content)
        assert action == "wait()"

    def test_hotkey_detected(self):
        content = "Press back.\nhotkey(key='Escape')"
        thinking, action = self._parse(content)
        assert action.startswith("hotkey(")

    def test_do_positional_arg_detected(self):
        content = "<answer>\ndo(Launch, app='华为坤灵')"
        thinking, action = self._parse(content)
        assert action.startswith("do(")

    def test_do_positional_without_answer_tag(self):
        content = "需要启动应用\ndo(Launch, app='华为坤灵')"
        thinking, action = self._parse(content)
        assert action == "do(Launch, app='华为坤灵')"


# ---------------------------------------------------------------------------
# Real-world regression: bare coordinates and positional args
# ---------------------------------------------------------------------------
class TestRealWorldRegressions:
    """Tests based on actual model outputs that previously failed."""

    def test_click_bare_coords(self):
        """click(start_box='(736,169)') — no <|box_start|> markers."""
        result = convert("click(start_box='(736,169)')")
        assert result == {"_metadata": "do", "action": "Tap", "element": [736, 169]}

    def test_click_bare_coords_with_spaces(self):
        result = convert("click(start_box='( 500 , 300 )')")
        assert result == {"_metadata": "do", "action": "Tap", "element": [500, 300]}

    def test_left_double_bare_coords(self):
        result = convert("left_double(start_box='(100,200)')")
        assert result == {
            "_metadata": "do",
            "action": "Double Tap",
            "element": [100, 200],
        }

    def test_right_single_bare_coords(self):
        result = convert("right_single(start_box='(300,400)')")
        assert result == {
            "_metadata": "do",
            "action": "Long Press",
            "element": [300, 400],
        }

    def test_scroll_bare_coords(self):
        result = convert("scroll(start_box='(500,500)', direction='down')")
        assert result["action"] == "Swipe"
        assert result["start"] == [500, 800]
        assert result["end"] == [500, 200]

    def test_drag_bare_coords(self):
        result = convert(
            "drag(start_box='(100,200)', end_box='(300,400)')"
        )
        assert result == {
            "_metadata": "do",
            "action": "Swipe",
            "start": [100, 200],
            "end": [300, 400],
        }

    def test_do_positional_launch(self):
        """do(Launch, app='华为坤灵') — Launch as positional arg, not action=."""
        from phone_agent.actions.handler import parse_action

        result = parse_action("do(Launch, app='华为坤灵')")
        assert result["_metadata"] == "do"
        assert result["action"] == "Launch"
        assert result["app"] == "华为坤灵"

    def test_do_positional_tap(self):
        """do(Tap, element=[500, 300]) — positional action name."""
        from phone_agent.actions.handler import parse_action

        result = parse_action("do(Tap, element=[500, 300])")
        assert result["action"] == "Tap"
        assert result["element"] == [500, 300]

    def test_do_positional_back(self):
        """do(Back) — single positional arg."""
        from phone_agent.actions.handler import parse_action

        result = parse_action("do(Back)")
        assert result["action"] == "Back"

    def test_click_bare_through_parse_action(self):
        """Full path: parse_action -> adapter for bare-coords click."""
        from phone_agent.actions.handler import parse_action

        result = parse_action("click(start_box='(736,169)')")
        assert result == {"_metadata": "do", "action": "Tap", "element": [736, 169]}

    def test_parse_response_then_parse_action_click_bare(self):
        """Full pipeline: _parse_response splits, then parse_action converts."""
        from phone_agent.actions.handler import parse_action
        from phone_agent.model.client import ModelClient

        client = ModelClient.__new__(ModelClient)
        content = (
            "<think>在桌面上找到华为坤灵图标\n"
            "Action: click(start_box='(736,169)')"
        )
        thinking, action_str = client._parse_response(content)
        assert action_str.startswith("click(")

        result = parse_action(action_str)
        assert result == {"_metadata": "do", "action": "Tap", "element": [736, 169]}

    def test_parse_response_then_parse_action_do_positional(self):
        """Full pipeline: do(Launch, app='华为坤灵') through both stages."""
        from phone_agent.actions.handler import parse_action
        from phone_agent.model.client import ModelClient

        client = ModelClient.__new__(ModelClient)
        content = "<answer>\ndo(Launch, app='华为坤灵')"
        thinking, action_str = client._parse_response(content)
        assert "do(" in action_str

        result = parse_action(action_str)
        assert result["action"] == "Launch"
        assert result["app"] == "华为坤灵"
