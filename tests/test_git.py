"""
Unit tests for the git module.
"""

import contextlib
from io import StringIO
from pathlib import Path

import git
import pytest

from giphon.git import _fetch_repository, handle_project

from .utils import MockLogger, MockRepository


def test_fetch_repository():
    """Test by capturing the outputs of the spoofed repository."""
    f = StringIO()

    with contextlib.redirect_stdout(f):
        _fetch_repository(MockRepository())
    output = f.getvalue()

    assert output == (
        "Would have fetched the repository\n"
        "Would have fetched the repository\n"
    )


def test_handle_project_with_dir(monkeypatch):
    """
    Test the `handle_project` when it doesn't clone repositories, but fetches
    new content.

    Tests by capturing the outputed messages of the Fake logger.
    """

    def mock_is_dir(_):
        return True

    def mock_clone_from(*args, **kwargs):
        return MockRepository(*args, **kwargs)

    monkeypatch.setattr(Path, "is_dir", mock_is_dir)
    monkeypatch.setattr(git.repo.Repo, "clone_from", mock_clone_from)
    monkeypatch.setattr(git.repo, "Repo", MockRepository)

    # Test behaviour when function is instructed to fetch
    fetch_output = StringIO()
    with contextlib.redirect_stdout(fetch_output):
        handle_project(
            repository_path=Path("toto"),
            repository_url="git@toto.com",  # Doesn't intervene
            fetch=True,
            logger=MockLogger(),
        )
    output = fetch_output.getvalue()

    assert output == (
        "Would have fetched the repository\n"
        "Would have fetched the repository\n"
    )

    # Test behaviour when function is instructed to not fetch
    no_fetch_output = StringIO()
    with contextlib.redirect_stdout(no_fetch_output):
        handle_project(
            repository_path=Path("toto"),
            repository_url="git@toto.com",  # Doesn't intervene
            fetch=False,
            logger=MockLogger(),
        )
    output = no_fetch_output.getvalue()

    assert output == ""


def test_handle_project_without_dir(monkeypatch):
    """
    Test the `handle_project` when it clones repositories and there is no
    returned exception.

    Tests by capturing the outputed messages of the Fake logger.
    """

    def mock_is_dir(_):
        return False

    def mock_clone_from(*args, **kwargs):
        print("Successfully fake-cloned")
        return MockRepository(*args, **kwargs)

    monkeypatch.setattr(Path, "is_dir", mock_is_dir)
    monkeypatch.setattr(git.Repo, "clone_from", mock_clone_from)

    f = StringIO()

    with contextlib.redirect_stdout(f):
        handle_project(
            repository_path=Path("toto"),
            repository_url="git@toto.com",  # Doesn't intervene
            fetch=False,  # Doesn't intervene
            logger=MockLogger(),  # Doesn't intervene
        )

    output = f.getvalue()

    assert output == "Successfully fake-cloned\n"


def test_handle_project_without_dir_and_handled_exception(monkeypatch):
    """
    Test the `handle_project` when it clones repositories and handles the
    returned exception.

    Tests by capturing the outputed messages of the Fake logger.
    """

    def mock_is_dir(_):
        return False

    def mock_clone_from(*args, **kwargs):
        raise git.GitCommandError(command="mock-clone", status=128)

    monkeypatch.setattr(Path, "is_dir", mock_is_dir)
    monkeypatch.setattr(git.Repo, "clone_from", mock_clone_from)

    f = StringIO()

    with contextlib.redirect_stdout(f):
        handle_project(
            repository_path=Path("toto"),
            repository_url="git@toto.com",  # Doesn't intervene
            fetch=False,  # Doesn't intervene
            logger=MockLogger(),  # Doesn't intervene
        )

    output = f.getvalue()

    assert output == (
        "Would have warned Cmd('mock-clone') failed due to: exit code(128)\n"
        "  cmdline: mock-clone with exc_info True\n"
    )


def test_handle_project_without_dir_and_unhandled_exception(monkeypatch):
    """
    Test the `handle_project` when it clones repositories and doesn't handle
    the returned exception.

    Tests by capturing verifying that the exception is re-raised.
    """

    def mock_is_dir(_):
        return False

    def mock_clone_from(*args, **kwargs):
        raise git.GitCommandError(command="clone", status=42)

    monkeypatch.setattr(Path, "is_dir", mock_is_dir)
    monkeypatch.setattr(git.Repo, "clone_from", mock_clone_from)

    with pytest.raises(git.GitCommandError):
        handle_project(
            repository_path=Path("toto"),
            repository_url="git@toto.com",  # Doesn't intervene
            fetch=False,  # Doesn't intervene
            logger=MockLogger(),  # Doesn't intervene
        )
