"""Tests for CLI interface."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from src.cli import BatchState, cli, get_output_filename, slugify


def test_slugify_basic():
    """Test basic slugification."""
    assert slugify("Hello World") == "hello-world"
    assert slugify("Test_Case_01") == "test-case-01"
    assert slugify("UPPERCASE") == "uppercase"


def test_slugify_special_chars():
    """Test slugification removes special characters."""
    assert slugify("Hello! World?") == "hello-world"
    assert slugify("test@case#01") == "testcase01"


def test_slugify_multiple_hyphens():
    """Test slugification normalizes multiple hyphens."""
    assert slugify("test---case") == "test-case"
    assert slugify("  test  case  ") == "test-case"


def test_get_output_filename_from_url():
    """Test filename extraction from URL."""
    url = "https://wiki.elecfreaks.com/en/case_01_test"
    filename = get_output_filename(url, "Some Title")

    assert "case" in filename.lower()


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "CoderDojo Guide Generator" in result.output


def test_cli_version():
    """Test CLI version command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_sources():
    """Test CLI sources command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["sources"])

    assert result.exit_code == 0
    assert "elecfreaks" in result.output.lower()


def test_cli_generate_missing_url():
    """Test CLI generate command requires URL."""
    runner = CliRunner()
    result = runner.invoke(cli, ["generate"])

    assert result.exit_code != 0
    assert "url" in result.output.lower()


def test_cli_batch_missing_index():
    """Test CLI batch command requires index URL."""
    runner = CliRunner()
    result = runner.invoke(cli, ["batch"])

    assert result.exit_code != 0
    assert "index" in result.output.lower()


def test_cli_batch_help():
    """Test CLI batch command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["batch", "--help"])

    assert result.exit_code == 0
    assert "index page" in result.output.lower()
    assert "--list-only" in result.output
    assert "--resume" in result.output


class TestBatchState:
    """Tests for BatchState class."""

    def test_batch_state_init(self):
        """Test BatchState initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            state = BatchState(output_dir)

            assert state.output_dir == output_dir
            assert state.state_path == output_dir / ".batch_state.json"
            assert len(state.completed) == 0
            assert len(state.failed) == 0
            assert state.index_url == ""

    def test_batch_state_save_and_load(self):
        """Test BatchState save and load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create and save state
            state1 = BatchState(output_dir)
            state1.index_url = "https://example.com/index"
            state1.completed.add("https://example.com/page1")
            state1.completed.add("https://example.com/page2")
            state1.failed.add("https://example.com/page3")
            state1.save()

            # Load state in new instance
            state2 = BatchState(output_dir)
            assert state2.load()
            assert state2.index_url == "https://example.com/index"
            assert "https://example.com/page1" in state2.completed
            assert "https://example.com/page2" in state2.completed
            assert "https://example.com/page3" in state2.failed

    def test_batch_state_mark_completed(self):
        """Test marking tutorials as completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            state = BatchState(output_dir)

            state.mark_completed("https://example.com/page1")
            assert state.is_completed("https://example.com/page1")
            assert not state.is_completed("https://example.com/page2")

    def test_batch_state_mark_failed_then_completed(self):
        """Test that completing a failed tutorial removes it from failed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            state = BatchState(output_dir)

            state.mark_failed("https://example.com/page1")
            assert "https://example.com/page1" in state.failed

            state.mark_completed("https://example.com/page1")
            assert "https://example.com/page1" in state.completed
            assert "https://example.com/page1" not in state.failed

    def test_batch_state_clear(self):
        """Test clearing batch state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            state = BatchState(output_dir)

            state.index_url = "https://example.com"
            state.completed.add("https://example.com/page1")
            state.save()

            assert state.state_path.exists()
            state.clear()

            assert not state.state_path.exists()
            assert len(state.completed) == 0
            assert state.index_url == ""

    def test_batch_state_load_nonexistent(self):
        """Test loading state when no file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            state = BatchState(output_dir)

            assert not state.load()
