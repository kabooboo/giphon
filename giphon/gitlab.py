import os

from pathlib import Path
from typing import Generator, List, Union

from gitlab import Gitlab
from gitlab.exceptions import GitlabListError
from gitlab.v4.objects import Group, Project


def save_environment_variables(path, element, logger):
    def _save_environment_variable(variable, env_path):

        scope = variable.environment_scope

        key = f'{variable.key}-{scope.replace("*", "star").replace("/", "-")}'

        with open(os.path.join(env_path, f"{key}"), "w") as f:
            f.write(variable.value)

    gitlab_element_path = os.path.join(
        path, get_gitlab_element_full_path(element)
    )
    env_path = os.path.join(gitlab_element_path, ".env")

    if not os.path.isdir(env_path):
        os.mkdir(env_path)

    el_type = get_gitlab_element_type(element)
    try:
        variables = element.variables.list(all=True)
        for variable in variables:
            _save_environment_variable(variable, env_path)

    except GitlabListError as e:
        logger.debug(e, exc_info=True)
        logger.debug(
            f"[Unable to save CI variables: {el_type} {element.name} "
            "has CI/CD disabled.]"
        )


def get_gitlab_element_type(element):
    if isinstance(element, Group):
        return "group"
    elif isinstance(element, Project):
        return "project"
    else:
        raise NotImplementedError(
            error=(f"Got unsupported gitlab object type {type(element)}")
        )


def get_gitlab_element_full_path(element):
    if isinstance(element, Group):
        return element.full_path
    elif isinstance(element, Project):
        return element.path_with_namespace
    else:
        raise NotImplementedError(
            error=(f"Got unsupported gitlab object type {type(element)}")
        )


def flatten_groups_tree(
    *, groups: List[Group], gl: Gitlab, archived: bool = False
) -> Generator[Union[Group, Project], None, None]:

    for group in groups:

        yield group

        yield from flatten_groups_tree(
            groups=[
                gl.groups.get(subgroup.id)
                for subgroup in group.subgroups.list(all=True)
            ],
            gl=gl,
            archived=archived,
        )
        for project in group.projects.list(all=True, archived=archived):
            yield gl.projects.get(project.id)


def get_gitlab_instance(*, url: str, private_token: str) -> Gitlab:
    return Gitlab(url=url, private_token=private_token)


def get_groups_from_path(namespace: str, gl: Gitlab) -> List[Group]:

    if namespace == Path("/"):
        groups = gl.groups.list(parent_id=None, iterator=True)
    else:
        groups = (gl.groups.get(namespace),)

    return groups
