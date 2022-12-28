"""
Unit tests for the siphon module.

Integration test for the main function.
"""

import os
from logging import INFO
from pathlib import Path
from sys import stderr, stdout
from tempfile import TemporaryDirectory

from giphon.siphon import _setup_logger, siphon


def test_setup_logger():
    """
    Test the behaviour of the `_setup_logger` function.
    """

    logger = _setup_logger(name="test_logger", log_level=INFO)

    assert len(logger.handlers) == 2

    assert any(handler.stream == stdout for handler in logger.handlers)
    assert any(handler.stream == stderr for handler in logger.handlers)

    logger.warning("this is a warning log")
    logger.critical("this is a critical error")
    logger.info("this is a info message")
    logger.debug("this is a debug message")

    stdout.seek(0)
    stderr.seek(0)

    out = stdout.read()
    err = stderr.read()

    assert "this is a warning log" in err
    assert "this is a critical error" in err
    assert "this is a info message" in out
    assert any(
        "this is a debug message" not in stream for stream in (out, err)
    )


def test_siphon(caplog):
    """
    Test the main function.

    I yet have no idea on how to test the main logic. Should I run an
    e2e test, directly against public gitlab?
    """

    with TemporaryDirectory() as temporary_directory:

        namespace = Path("gitlab-org/ci-cd/shared-runners")
        output = Path(temporary_directory)

        siphon(
            namespace=namespace,
            output=output,
            gitlab_token="",
            gitlab_url="https://gitlab.com",
            fetch_repositories=True,
            save_ci_variables=False,  # Cannot save variables on public repos
            clone_archived=False,
            clone_through_ssh=False,
            verbose=False,
        )

        print(caplog)

        assert os.path.isdir(str(output / namespace / Path("homebrew/.git")))
        assert os.path.isdir(str(output / namespace / Path("macos/.git")))
        assert os.path.isdir(str(output / namespace / Path("macos/.git")))
        assert os.path.isdir(
            str(
                output / namespace / Path("images/gcp/windows-containers/.git")
            )
        )
