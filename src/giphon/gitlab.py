import os
from logging import Logger
from pathlib import Path
from typing import Generator, List, Union

from gitlab import Gitlab
from gitlab.base import RESTObject
from gitlab.exceptions import GitlabHttpError, GitlabListError
from gitlab.v4.objects import Group, GroupVariable, Project, ProjectVariable

Variable = Union[ProjectVariable, GroupVariable]


def save_environment_variables(
    path: Path, element: RESTObject, logger: Logger
) -> None:
    """
    Save environment variables locally for a given Gitlab group or project.

    Args:
        path (Path): the path to save the environment variables to
        element (Union[gitlab.v4.objects.Group, gitlab.v4.objects.Project]):
          The Gitlab group or project to get the environment variables from
        logger (Logger): the logger to use to generate logs
    """

    def _save_environment_variable(variable: Variable, env_path: Path) -> None:
        scope = variable.environment_scope

        key = f'{variable.key}-{scope.replace("*", "STAR").replace("/", "-")}'

        with open(os.path.join(env_path, f"{key}"), "w") as f:
            f.write(variable.value)

    gitlab_element_path = os.path.join(
        path, get_gitlab_element_full_path(element)
    )
    env_path = gitlab_element_path / Path(".gitlab/.env")

    if not os.path.isdir(env_path):
        os.makedirs(env_path, exist_ok=True)

    el_type = get_gitlab_element_type(element)
    try:
        variables = element.variables.list(all=True)
        for variable in variables:
            _save_environment_variable(variable, env_path)

    except (GitlabListError, GitlabHttpError) as e:
        logger.debug(e, exc_info=True)
        logger.debug(
            f"[Unable to save CI variables: {el_type} {element.name} "
            "has CI/CD disabled.]"
        )


def get_gitlab_element_type(element: RESTObject) -> str:
    """
    Get a pretty-printable string representing the element's type.

    Args:
        element (Union[gitlab.v4.objects.Group, gitlab.v4.objects.Project]):
          The Gitlab group or project to get the type as a string

    Raises:
        NotImplementedError: Whether the type of `element` is unsupported

    Returns:
        str: String representing `element`'s type
    """
    if isinstance(element, Group):
        return "group"
    elif isinstance(element, Project):
        return "project"
    else:
        raise NotImplementedError(
            f"Got unsupported gitlab object type {type(element)}\n"
            f"Excpected {Group} or {Project}"
        )


def get_gitlab_element_full_path(element: RESTObject) -> Path:
    """
    Get the full path of a given Gitlab Element

    Args:
        element (Union[gitlab.v4.objects.Group, gitlab.v4.objects.Project]):
          The Gitlab group or project to get the full path

    Raises:
        NotImplementedError: Whether the type of `element` is unsupported

    Returns:
        Path: the full path for the element
    """
    if isinstance(element, Group):
        return Path(element.full_path)
    elif isinstance(element, Project):
        return Path(element.path_with_namespace)
    else:
        raise NotImplementedError(
            f"Got unsupported gitlab object type {type(element)}"
            f"Excpected {Group} or {Project}"
        )

def get_gitlab_instance(*, url: str, private_token: str) -> Gitlab:
    """
    Get a Python Gitlab API instance

    Args:
        url (str): The URL of the Gitlab instance
        private_token (str): A private token capable to access the instance.

    Returns:
        Gitlab: The Python Gitlab API instance
    """
    return Gitlab(url=url, private_token=private_token)


def get_groups_from_path(namespace: Path, gl: Gitlab) -> List[RESTObject]:
    """
    Get a list of Gitlab groups contained in a given namespace.

    Args:
        namespace (str): The namespace to get the groups from.
        gl (Gitlab): the Gitlab API instance.

    Returns:
        List[Group]: THe list of Gitlab groups in `namespace`.
    """

    if namespace == Path("/"):
        groups = [el for el in gl.groups.list(parent_id=None, iterator=True)]
    else:
        groups = [gl.groups.get(str(namespace))]

    return groups
