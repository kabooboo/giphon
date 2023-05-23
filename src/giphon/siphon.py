import logging
from pathlib import Path
from sys import stderr, stdout
from typing import Optional
from urllib.parse import urlparse, urlunparse
from multiprocessing import Pool

from gitlab.v4.objects import Project
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from typer import Option

from .git import call_handle, handle_project
from .gitlab import (
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
    gitlab_username: Optional[str] = Option(
        "",
        help=(
            "The Username associated with the Access Token. Used for cloning"
            "through https."
        ),
        envvar="GITLAB_USERNAME",
    ),
    verbose: bool = Option(
        False,
        "--verbose",
        "-v",
        help=("The level of verbosity."),
    ),
    using_multiprocessing: Optional[bool] = Option(
        False,
        help="Whether cloning the repositories in parallel (be careful, you could reach rate limiting limits)",
    )
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
        clone_through_ssh (bool, optional): Whether to clone using ssh or
          https.
        gitlab_username: (str, optional): The username to use when cloning
          through https.
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
            description="Giphoning all the projects...", total=None
        )

        gl = get_gitlab_instance(url=gitlab_url, private_token=gitlab_token)

        groups = get_groups_from_path(namespace, gl)

        all_project = []

        for group in groups:
            tmp_group = gl.groups.get(group.id)
            project_in_group = tmp_group.projects.list(include_subgroups=True, all=True, archived=clone_archived)
            all_project = all_project + project_in_group
            progress.update(flat_tree_task_id, advance=len(project_in_group))

    logger.info(f"Found {len(all_project)} projects to clone")

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TextColumn("[progress.description] {task.description}"),
        transient=True,
    ) as progress:
        clone_task_id = progress.add_task(description="Cloning", total=len(all_project))

        project_cloning_arguments = []

        cloning_iterable = all_project if using_multiprocessing else progress.track(all_project, task_id=clone_task_id)

        for element in cloning_iterable:
            if clone_through_ssh:
                url_to_repo = element.ssh_url_to_repo
            elif not clone_through_ssh and gitlab_username:
                parsed_url_to_repo = urlparse(element.http_url_to_repo)

                unauthenticated_domain = parsed_url_to_repo.netloc.split(
                    "@"
                )[-1]

                authenticated_domain = (
                    f"{gitlab_username}:{gitlab_token}"
                    f"@{unauthenticated_domain}"
                )

                unparsed_url_args = (
                    parsed_url_to_repo[0],
                    authenticated_domain
                    if gitlab_username != ""
                    else unauthenticated_domain,
                    parsed_url_to_repo[2],
                    parsed_url_to_repo[3],
                    parsed_url_to_repo[4],
                    parsed_url_to_repo[5],
                )

                url_to_repo = urlunparse(unparsed_url_args)
            else:
                url_to_repo = element.http_url_to_repo

            if not using_multiprocessing:
                progress.update(clone_task_id, description=f"Done cloning {element.path_with_namespace}", advance=1)

                handle_project(
                    repository_path=output / Path(element.path_with_namespace),
                    repository_url=url_to_repo,
                    fetch=bool(fetch_repositories),
                    logger=logger,
                )
            else:
                project_cloning_arguments.append([
                    output / Path(element.path_with_namespace),
                    url_to_repo,
                    bool(fetch_repositories),
                    logger,
                ])

        if using_multiprocessing:
            with Pool() as pool:
                results = pool.imap(call_handle, project_cloning_arguments)
                for repo in results:
                    # do not work very well ? maybe a locking issue ?
                    progress.update(clone_task_id, description=f"Done cloning {repo}", advance=1)

        if save_ci_variables:
            for element in all_project:
                save_environment_variables(output, element, logger)

        logger.info(f"\nDone cloning all the projects!")
