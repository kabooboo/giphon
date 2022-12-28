"""
Unit tests for the gitlab module.
"""

import builtins
import contextlib
import os
from io import StringIO
from pathlib import Path

import gitlab
import pytest

from giphon.gitlab import (
    flatten_groups_tree,
    get_gitlab_element_full_path,
    get_gitlab_element_type,
    get_gitlab_instance,
    get_groups_from_path,
    save_environment_variables,
)

from .utils import (
    MockGitlab,
    MockGitlabGroup,
    MockGitlabProject,
    MockGitlabVariables,
    MockLogger,
)


def test_get_gitlab_instance(monkeypatch):
    """
    Test whether the function `get_gitlab_instance` works properly.

    This is tested by monkeypatching the `gitlab.Gitlab` class.
    """

    monkeypatch.setattr(gitlab, "Gitlab", MockGitlab)

    gl = get_gitlab_instance(url="https://test", private_token="SECRET")

    assert gl.url == "https://test"
    assert gl.private_token == "SECRET"

    assert isinstance(gl, gitlab.client.Gitlab)


def test_get_gitlab_element_type(monkeypatch):
    """
    Test whether the function `get_gitlab_element_type` works properly.

    This is tested by monkeypatching the gitlab attributes'
    (`gitlab.v4.objects.groups.Group`, `gitlab.v4.objects.projects.Project`)
    __init__ function, so we can use the real object.

    """

    def mock_init(self, *args, **kwargs) -> None:
        self.__dict__["_updated_attrs"] = {}
        print(f"Entered mock init with {args} args and {kwargs} kwargs")

    monkeypatch.setattr(
        gitlab.v4.objects.groups.Group,
        "__init__",
        mock_init,
    )
    monkeypatch.setattr(
        gitlab.v4.objects.projects.Project,
        "__init__",
        mock_init,
    )
    monkeypatch.setattr(
        gitlab.v4.objects.users.User,
        "__init__",
        mock_init,
    )

    el = get_gitlab_element_type(gitlab.v4.objects.groups.Group())

    assert el == "group"

    el = get_gitlab_element_type(gitlab.v4.objects.projects.Project())

    assert el == "project"

    with pytest.raises(NotImplementedError):
        el = get_gitlab_element_type(gitlab.v4.objects.users.User())


def test_get_gitlab_element_full_path(monkeypatch):
    """
    Test whether the function `get_gitlab_element_full_path` works properly.

    This is tested by monkeypatching the gitlab attributes'
    (`gitlab.v4.objects.groups.Group`, `gitlab.v4.objects.projects.Project`)
    __init__ function, so we can use the real object and by monkeypatching the
    base `RESTObject` from gitlab

    """

    def mock_init(
        self, mock_full_path, mock_path_with_namespace, *args
    ) -> None:
        self.full_path = mock_full_path
        self.path_with_namespace = mock_path_with_namespace

    # Monkeypatch setters and getters
    monkeypatch.delattr(gitlab.base.RESTObject, "__getattr__")
    monkeypatch.delattr(gitlab.base.RESTObject, "__setattr__")

    # Monkeypatch constructors
    monkeypatch.setattr(
        gitlab.v4.objects.groups.Group,
        "__init__",
        mock_init,
    )
    monkeypatch.setattr(
        gitlab.v4.objects.projects.Project,
        "__init__",
        mock_init,
    )
    monkeypatch.setattr(
        gitlab.v4.objects.users.User,
        "__init__",
        mock_init,
    )

    # Groups should return full_path
    el = get_gitlab_element_full_path(
        gitlab.v4.objects.groups.Group(
            mock_full_path="lorem",
            mock_path_with_namespace="ipsum",
        )
    )

    assert str(el) == "lorem"

    # Projects should return path_with_namespace
    el = get_gitlab_element_full_path(
        gitlab.v4.objects.projects.Project(
            mock_full_path="lorem",
            mock_path_with_namespace="ipsum",
        )
    )

    assert str(el) == "ipsum"

    # Others should raise NotImplementedError
    with pytest.raises(NotImplementedError):
        el = get_gitlab_element_full_path(
            gitlab.v4.objects.users.User(
                mock_full_path="lorem",
                mock_path_with_namespace="ipsum",
            )
        )


def test_get_groups_from_path():
    """
    Test whether the function `get_groups_from_path` works properly.

    This is tested by Mocking the gitlab instance.

    """
    gl = MockGitlab(
        url="https://toto",
        private_token="SECRET",
    )

    gl.groups._groups = [
        MockGitlabGroup(id="/first"),
        MockGitlabGroup(id="/second"),
        MockGitlabGroup(id="/third"),
    ]

    # test the root path
    groups = get_groups_from_path(
        namespace=Path("/"),
        gl=gl,
    )

    assert len(groups) == 3

    assert all(isinstance(group, MockGitlabGroup) for group in groups)

    assert groups[0].id == "/first"
    assert groups[1].id == "/second"
    assert groups[2].id == "/third"

    # test any path
    group = get_groups_from_path(
        namespace=Path("/first"),
        gl=gl,
    )

    assert isinstance(group[0], MockGitlabGroup)

    assert group[0].id == "/first"


def test_save_environment_variables(monkeypatch):
    """
    Test the `save_environment_variables` function.

    This is done by monkeypatching:
      - the getters and setters of gitlab.base.RESTObect
      - the `__init__` of gitlab Groups
      - `open` and `os.makedirs`

    """

    def mock_init(
        self,
        mock_full_path,
        mock_path_with_namespace,
        *_,
    ) -> None:
        self.full_path = mock_full_path
        self.path_with_namespace = mock_path_with_namespace
        self.variables = MockGitlabVariables()

    def mock_init_errored_variables(
        self, mock_full_path, mock_path_with_namespace, mock_name="", *args
    ) -> None:
        self.full_path = mock_full_path
        self.path_with_namespace = mock_path_with_namespace
        self.name = mock_name
        self.variables = MockGitlabVariables(list_must_error=True)

    def mock_open(*args, **kwargs):
        print(f"Entered mock open with args {args} and kwargs {kwargs}")

        class FakeIO:
            def write(self, value):
                print(f"Would have written {value}")

            def __enter__(self, *_):
                return self

            def __exit__(self, *_):
                pass

        return FakeIO()

    def mock_makedirs(path, **_):
        print(f"Would have made the path {path}")

    # Monkeypatch setters and getters
    monkeypatch.delattr(gitlab.base.RESTObject, "__getattr__")
    monkeypatch.delattr(gitlab.base.RESTObject, "__setattr__")

    # Monkeypatch constructors
    monkeypatch.setattr(builtins, "open", mock_open)
    monkeypatch.setattr(os, "makedirs", mock_makedirs)

    # Initialize mock loggers
    logger = MockLogger()

    # Monkeypatch group with variables, without exception raised
    with monkeypatch.context() as m:
        m.setattr(gitlab.v4.objects.groups.Group, "__init__", mock_init)

        group_without_variable_errors = gitlab.v4.objects.groups.Group(
            mock_full_path="the_group",
            mock_path_with_namespace="_",
        )

        no_error_output = StringIO()

        with contextlib.redirect_stdout(no_error_output):
            save_environment_variables(
                path=Path("random_path"),
                element=group_without_variable_errors,
                logger=logger,
            )

        output = no_error_output.getvalue()
        # Test the stdout of the function

        assert output == (
            "Would have made the path random_path/the_group/.gitlab/.env\n"
            "Entered mock open with args ('random_path/the_group/.gitlab/.env/"
            "ipsum-lorem', 'w') and kwargs {}\n"
            "Would have written dolor\n"
            "Entered mock open with args ('random_path/the_group/.gitlab/.env/"
            "ipsum-lorem', 'w') and kwargs {}\n"
            "Would have written dolor\n"
            "Entered mock open with args ('random_path/the_group/.gitlab/.env/"
            "ipsum-lorem', 'w') and kwargs {}\n"
            "Would have written dolor\n"
        )

    # Monkeypatch group with variables, but listing variables raises an
    # exception
    with monkeypatch.context() as m:
        m.setattr(
            gitlab.v4.objects.groups.Group,
            "__init__",
            mock_init_errored_variables,
        )

        group_with_variable_errors = gitlab.v4.objects.groups.Group(
            mock_full_path="the_group",
            mock_path_with_namespace="_",
            mock_name="mock_group",
        )

        errored_ouput = StringIO()

        with contextlib.redirect_stdout(errored_ouput):
            save_environment_variables(
                path=Path("random_path"),
                element=group_with_variable_errors,
                logger=logger,
            )

        output = errored_ouput.getvalue()
        # Test the stdout of the function

        assert output == (
            "Would have made the path random_path/the_group/.gitlab/.env\n"
            "Would have debugged  with exc_info True\n"
            "Would have debugged [Unable to save CI variables: group "
            "mock_group has CI/CD disabled.] with exc_info None\n"
        )


def test_flatten_groups_tree():
    """
    Test the `flatten_groups_tree` function.

    This is done by Mocking the gitlab instance and checking whether the tree
    is flattened correclty.


    """
    foo = MockGitlabProject(id="foo")
    faa = MockGitlabProject(id="faa")

    bar = MockGitlabProject(id="bar")
    baz = MockGitlabProject(id="baz")

    ipsum = MockGitlabGroup(
        id="ipsum",
        projects=[foo, faa],
    )

    amet = MockGitlabGroup(id="amet")

    lorem = MockGitlabGroup(
        id="lorem",
        subgroups=[
            ipsum,
            amet,
        ],
        projects=[
            bar,
            baz,
        ],
    )
    dolor = MockGitlabGroup(id="dolor")

    # Build a custom group tree to test
    groups = [
        lorem,
        dolor,
    ]

    gl = MockGitlab(
        url="https://toto",
        private_token="SECRET",
    )
    gl.groups._groups = [lorem, ipsum, amet, dolor]
    gl.projects._projects = [foo, faa, bar, baz]

    r = flatten_groups_tree(
        groups=groups,
        gl=gl,
        archived=True,
    )

    assert [k.id for k in r] == [
        "lorem",
        "ipsum",
        "foo",
        "faa",
        "amet",
        "bar",
        "baz",
        "dolor",
    ]
