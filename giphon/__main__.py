#!/usr/bin/python3

import os
import re

from pathlib import Path
from typing import Optional

import git
import gitlab

from gitlab.v4.objects import Group
from ruamel.yaml import YAML
from typer import Option, Typer


yaml = YAML()

app = Typer(no_args_is_help=True, add_completion=False)

# TODO: use loggers
# TODO: add docstrings
# TODO: add typehints
# TODO: add tests
# TODO: add CI
# TODO: publish package


def _clone(
    current_path, gitlab_element, gl, fetch, save_ci_variables, depth=0
):
    clone_function = (
        _clone_group if isinstance(gitlab_element, Group) else _clone_project
    )
    clone_function(
        current_path, gitlab_element, gl, fetch, save_ci_variables, depth=depth
    )

    if save_ci_variables:
        _save_environment_variables(current_path, gitlab_element)


def _clone_group(current_path, group, gl, fetch, save_ci_variables, depth=0):

    print(
        f"{' ├' if depth > 0 else ''}{'───' * depth + ' '}handling "
        f"group {group.name}"
    )

    group_path = os.path.join(current_path, group.path)

    if not os.path.isdir(group_path):
        os.mkdir(group_path)

    any(
        _clone(
            group_path,
            gl.projects.get(id=project.id),
            gl,
            fetch,
            save_ci_variables,
            depth=depth + 1,
        )
        for project in group.projects.list(all=True, archived=False)
    )

    any(
        _clone(
            group_path,
            gl.groups.get(id=subgroup.id),
            gl,
            fetch,
            depth=depth + 1,
        )
        for subgroup in group.subgroups.list(all=True)
    )


def _clone_project(current_path, project, _, fetch, __, depth=0):

    print(
        f"{' ├' if depth > 0 else ''}{'───' * depth + ' '}handling "
        f"project {project.name}"
    )

    repo_url = project.ssh_url_to_repo
    repo_path = os.path.join(current_path, project.path)

    if not os.path.isdir(repo_path):
        while "Trying to clone the repo":
            try:
                repo = git.Repo.clone_from(
                    repo_url, repo_path, no_single_branch=True
                )
                break
            except git.exc.GitCommandError as e:
                if e.status == 128:
                    print(e)
                    return
                else:
                    raise e
            except Exception as e:
                print(e)
    else:
        if fetch:
            repo = git.Repo(repo_path)
            _fetch_repo(repo)


def _fetch_repo(repo):
    for remote in repo.remotes:
        remote.fetch()


def _save_environment_variables(current_path, gitlab_element):
    def _save_environment_variable(variable, env_path):

        scope = variable.environment_scope

        key = (
            variable.key
            if scope == "*"
            else f"{variable.key}-{re.sub('[^0-9a-zA-Z]+', '-', scope)}"
        )

        with open(os.path.join(env_path, f"{key}"), "w") as f:
            f.write(variable.value)

    gitlab_element_path = os.path.join(current_path, gitlab_element.path)
    env_path = os.path.join(gitlab_element_path, ".env")

    if not os.path.isdir(env_path):
        os.mkdir(env_path)

    any(
        _save_environment_variable(variable, env_path)
        for variable in gitlab_element.variables.list(all=True)
    )


@app.command()
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
    fetch: Optional[bool] = True,
    save_ci_variables: Optional[bool] = True,
):
    """
    Clone repositories from a Gitlab group or instance.
    """

    gl = gitlab.Gitlab(url=gitlab_url, private_token=gitlab_token)

    if namespace == Path("/"):
        groups = gl.groups.list(parent_id=None, iterator=True)
    else:
        groups = (gl.groups.get(namespace),)

    all(
        _clone(output, group, gl, fetch, save_ci_variables, depth=0)
        for group in groups
    )


if __name__ == "__main__":
    app()
