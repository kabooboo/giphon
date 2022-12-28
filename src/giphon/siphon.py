import logging
from pathlib import Path
from sys import stderr, stdout
from typing import Optional

from gitlab.v4.objects import Project
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from typer import Option

from .git import handle_project
from .gitlab import (
    flatten_groups_tree,
    get_gitlab_element_full_path,
    get_gitlab_element_type,
    get_gitlab_instance,
    get_groups_from_path,
    save_environment_variables,
)


def _setup_logger(name: str, log_level: int) -> logging.Logger:
    class _InfoFilter(logging.Filter):
        def filter(self: "_InfoFilter", rec: logging.LogRecord) -> bool:
            return rec.levelno in (logging.DEBUG, logging.INFO)

    logger = logging.getLogger(name)

    logger.setLevel(log_level)

    stdout_handler = logging.StreamHandler(stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.addFilter(_InfoFilter())
    stderr_handler = logging.StreamHandler(stderr)
    stderr_handler.setLevel(logging.WARNING)

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    return logger


def siphon(
    *,
    namespace: Path = Option(
        ...,
        help=(
            "The Gitlab namespace to recusively siphon. "
            "Use `/` to siphon the instance."
        ),
    ),
    output: Path = Option(
        ...,
        help="The target path to clone the repositories to.",
    ),
    gitlab_token: str = Option(
        ...,
        help="The Personal Access Token for the Gitlab v4 API.",
        envvar="GITLAB_TOKEN",
    ),
    gitlab_url: str = Option(
        "https://gitlab.com",
        help="The URL for the Gitlab Instance.",
        envvar="GITLAB_URL",
    ),
    fetch_repositories: Optional[bool] = Option(
        True,
        help="Whether to fetch remotes on repositories that already exist.",
    ),
    save_ci_variables: Optional[bool] = Option(
        True,
        help="Whether to download CI/CD variables to a .env directory.",
    ),
    clone_archived: Optional[bool] = Option(
        False,
        help="Whether to clone archived repository.",
    ),
    clone_through_ssh: Optional[bool] = Option(
        True,
        help="Whether to clone repositories through SSH (Default) or https.",
    ),
    verbose: bool = Option(
        False,
        "--verbose",
        "-v",
        help=("The level of verbosity."),
    ),
) -> None:
    """
    Siphon contents from a Gitlab instance or group.

    This function traverses recursively a Gitlab instance or group in order to
    copy locally all of the project's repositories and their environment
    variables, while keeping the arborescence.

    Args:
        namespace (Path): The Gitlab namespace to recusively siphon.
          Use `/` to siphon the instance.
        output (Path): The target path to clone the repositories to.", ).
        gitlab_token (str): The Personal Access Token for the Gitlab v4 API."
        gitlab_url (str): The URL for the Gitlab Instance. Defaults to
          "https://gitlab.com".
        fetch_repositories (bool, optional): Whether to fetch remotes on
          repositories that already exist. Defaults to True.
        save_ci_variables (bool, optional): Whether to download CI/CD
          variables to a .env directory.. Defaults to True.
        clone_archived (bool, optional): Whether to clone archived repository.
          Defaults to False.
        verbose (bool, optional): Whether the outputs should be verbose.
          Defaults to False.

    """
    logger = _setup_logger(
        __name__, logging.INFO if verbose <= 0 else logging.DEBUG
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description] {task.description}"),
        transient=True,
    ) as progress:

        flat_tree_task_id = progress.add_task(
            description="Looking for stuff to siphon...", total=None
        )

        gl = get_gitlab_instance(url=gitlab_url, private_token=gitlab_token)

        groups = get_groups_from_path(namespace, gl)

        flat_tree = []

        for index, element in enumerate(
            flatten_groups_tree(
                groups=groups, gl=gl, archived=bool(clone_archived)
            )
        ):
            progress.update(
                flat_tree_task_id,
                advance=1,
                description=f"Found {index} elements...",
            )
            flat_tree.append(element)

    with Progress(
        SpinnerColumn(),
        MofNCompleteColumn(),
        BarColumn(),
        TextColumn("[progress.description] {task.description}"),
        transient=True,
    ) as progress:

        clone_task_id = progress.add_task(description="Cloning")

        processed = 0

        for element in progress.track(flat_tree, task_id=clone_task_id):

            element_type = get_gitlab_element_type(element)
            element_full_path = get_gitlab_element_full_path(element)

            progress.update(
                clone_task_id,
                description=(f"Handling {element_type} {element_full_path}"),
            )

            if isinstance(element, Project):

                url_to_repo = (
                    element.ssh_url_to_repo
                    if clone_through_ssh
                    else element.http_url_to_repo
                )

                handle_project(
                    repository_path=output / Path(element.path_with_namespace),
                    repository_url=url_to_repo,
                    fetch=bool(fetch_repositories),
                    logger=logger,
                )

            if save_ci_variables:
                save_environment_variables(output, element, logger)

            processed += 1

        logger.info(f"Done cloning {processed} elements.")
