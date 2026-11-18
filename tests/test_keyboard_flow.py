import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "1.py"
SPEC = importlib.util.spec_from_file_location("teacher_review_script", SCRIPT_PATH)
script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(script)


class FakeUI:
    def __init__(self):
        self.calls = []

    def hotkey(self, *keys):
        self.calls.append(("hotkey", keys))

    def press(self, key):
        self.calls.append(("press", key))

    def write(self, text):
        self.calls.append(("write", text))


class FakeWindow:
    def __init__(self, title, left=0, top=0, width=0, height=0):
        self.title = title
        self.left = left
        self.top = top
        self.width = width
        self.height = height


class FakeScrollUI:
    def __init__(self):
        self.calls = []

    def moveTo(self, x, y):
        self.calls.append(("moveTo", x, y))

    def scroll(self, amount):
        self.calls.append(("scroll", amount))


class KeyboardFlowTests(unittest.TestCase):
    def test_type_scores_by_tab_fills_every_score_and_tabs_between_fields(self):
        ui = FakeUI()

        script.type_scores_by_tab(ui, score_value="20", score_count=3, input_interval=0)

        self.assertEqual(
            ui.calls,
            [
                ("hotkey", ("ctrl", "a")),
                ("press", "backspace"),
                ("write", "20"),
                ("press", "tab"),
                ("hotkey", ("ctrl", "a")),
                ("press", "backspace"),
                ("write", "20"),
                ("press", "tab"),
                ("hotkey", ("ctrl", "a")),
                ("press", "backspace"),
                ("write", "20"),
            ],
        )

    def test_choose_target_window_prefers_first_title_keyword_match(self):
        windows = [
            FakeWindow("浏览器"),
            FakeWindow("企业微信"),
            FakeWindow("WeChat"),
        ]

        chosen = script.choose_target_window(windows, ("微信", "WeChat"))

        self.assertIs(chosen, windows[1])

    def test_default_window_keywords_prefer_miniprogram_title(self):
        windows = [
            FakeWindow("微信"),
            FakeWindow("打分测评"),
        ]

        chosen = script.choose_target_window(windows)

        self.assertIs(chosen, windows[1])

    def test_scroll_uses_target_window_content_point(self):
        ui = FakeScrollUI()
        window = FakeWindow("打分测评", left=100, top=50, width=400, height=800)

        script.scroll_in_target_window(-300, target_window=window, ui=ui, method="wheel", delay=0)

        self.assertEqual(ui.calls, [("moveTo", 300, 490), ("scroll", -300)])

    def test_missing_resources_reports_only_absent_files(self):
        original_resource_path = script.resource_path
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "exists.png").write_text("x", encoding="utf-8")
            script.resource_path = lambda filename: str(temp_path / filename)

            try:
                missing = script.missing_resources(("exists.png", "missing.png"))
            finally:
                script.resource_path = original_resource_path

        self.assertEqual(missing, ["missing.png"])


if __name__ == "__main__":
    unittest.main()
