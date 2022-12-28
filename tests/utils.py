"""
Mocking utilities.
"""

from typing import Iterator

from gitlab.exceptions import GitlabListError


# Logger
class MockLogger:
    def warning(self: "MockLogger", message, exc_info: bool = None) -> None:
        print(f"Would have warned {message} with exc_info {exc_info}")

    def debug(self: "MockLogger", message, exc_info: bool = None) -> None:
        print(f"Would have debugged {message} with exc_info {exc_info}")


# Git
class MockRepository:
    def __init__(
        self: "MockRepository",
        repository_url: str = None,
        repository_patch: str = None,
        **_,
    ) -> None:
        self.repository_url = repository_url
        self.repository_patch = repository_patch
        self.remotes = [_MockRepositoryRemote(), _MockRepositoryRemote()]


class _MockRepositoryRemote:
    def fetch(self: "_MockRepositoryRemote") -> None:
        print("Would have fetched the repository")


# Gitlab
class MockGitlab:
    def __init__(self: "MockGitlab", url: str, private_token: str) -> None:
        self.url = url
        self.private_token = private_token
        self.groups = _MockGitlabGroupList()
        self.projects = _MockGitlabProjectList()


class _MockGitlabProjectList:
    def __init__(self: "_MockGitlabProjectList", *args, **kwargs):
        print(
            f"Entered initialize of {type(self)} with args {args} and "
            f"kwargs {kwargs}"
        )
        self._projects = []

    def list(self, *args, **kwargs) -> Iterator:
        return self._projects

    def get(self, id, *args, **kwargs) -> "MockGitlabProject":
        return next(project for project in self._projects if project.id == id)


class _MockGitlabGroupList:
    def __init__(self: "MockGitlabGroup", *args, **kwargs):
        print(
            f"Entered initialize of {type(self)} with args {args} and "
            f"kwargs {kwargs}"
        )
        self._groups = []

    def list(self, *args, **kwargs) -> Iterator:
        return self._groups

    def get(self, id, *args, **kwargs) -> "MockGitlabGroup":
        return next((group for group in self._groups if group.id == id))


class MockGitlabProject:
    def __init__(
        self: "MockGitlabProject",
        id,
        *args,
        **kwargs,
    ):
        print(f"Entered initialize of {type(self)} with id {id}")
        self.id = id


class MockGitlabGroup:
    def __init__(
        self: "MockGitlabGroup",
        *args,
        id=None,
        subgroups=None,
        projects=None,
        **kwargs,
    ):
        print(f"Entered initialize of {type(self)} with id {id}")
        self.id = id
        self.subgroups = _MockGitlabSubgroups(subgroups=subgroups)
        self.projects = _MockGitlabGroupProjects(projects=projects)


class _MockGitlabSubgroups:
    def __init__(self, *args, subgroups=None, **kwargs):
        print(f"Entered initialize of {type(self)} with subgroups {subgroups}")
        self.subgroups = subgroups

    def list(self, *args, **kwargs):
        return self.subgroups if self.subgroups else []


class _MockGitlabGroupProjects:
    def __init__(self, *args, projects=None, **kwargs):
        print(f"Entered initialize of {type(self)} with projects {projects}")
        self.projects = projects

    def list(self, *args, **kwargs):
        return self.projects if self.projects else []


class MockGitlabVariables:
    def __init__(
        self: "MockGitlabVariables", *args, list_must_error=False, **kwargs
    ):
        print(
            f"Entered initialize of {type(self)} with args {args} and "
            f"kwargs {kwargs}"
        )
        self.list_must_error = list_must_error

    def list(self, *args, **kwargs):
        if self.list_must_error:
            raise GitlabListError
        return [
            _MockGitlabVariable(),
            _MockGitlabVariable(),
            _MockGitlabVariable(),
        ]


class _MockGitlabVariable:
    def __init__(self, *args, **kwargs):
        self.environment_scope = "lorem"
        self.key = "ipsum"
        self.value = "dolor"
