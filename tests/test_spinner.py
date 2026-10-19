import io
import time
import unittest
from unittest.mock import Mock, patch

from gitbot import spinner


class SpinnerTests(unittest.TestCase):
    def test_fit_preserves_short_text(self):
        result = spinner._fit("⠋", "short text", 2.0, 80)
        self.assertEqual(result, "⠋ short text 2s")

    def test_fit_truncates_long_text_to_fit_columns(self):
        text = "generating commit message · claude-cli / sonnet · 1 file(s), 17 line(s)"
        for cols in (40, 50, 60, 70, 71, 75, 80):
            with self.subTest(cols=cols):
                line = spinner._fit("⠋", text, 5.0, cols)
                self.assertLessEqual(len(line), max(10, cols - 1))
                self.assertTrue(line.startswith("⠋ "))
                self.assertTrue(line.endswith(" 5s"))
                if len(f"⠋ {text} 5s") > max(10, cols - 1):
                    self.assertIn("…", line)

    def test_spin_no_op_when_not_a_tty(self):
        mock_stderr = Mock()
        mock_stderr.isatty.return_value = False
        with patch.object(spinner.sys, "stderr", mock_stderr):
            with spinner.spin("test"):
                pass
        mock_stderr.write.assert_not_called()

    def test_spin_writes_disable_wrap_and_restores_enable_wrap(self):
        fake_stderr = io.StringIO()
        fake_stderr.isatty = lambda: True
        with patch.object(spinner.sys, "stderr", fake_stderr), \
                patch.object(spinner, "_terminal_columns", return_value=70):
            with spinner.spin("testing spinner"):
                time.sleep(0.12)
        output = fake_stderr.getvalue()
        self.assertIn(spinner.HIDE_CURSOR, output)
        self.assertIn(spinner.DISABLE_WRAP, output)
        self.assertIn(spinner.ENABLE_WRAP, output)
        self.assertIn(spinner.SHOW_CURSOR, output)


if __name__ == "__main__":
    unittest.main()

