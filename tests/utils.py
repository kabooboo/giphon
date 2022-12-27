class FakeLogger:
    def warning(self: "FakeLogger", message, exc_info: bool = None) -> None:
        print(f"Would have logged {message} with exc_info {exc_info}")


class FakeRepository:
    def __init__(
        self: "FakeRepository",
        repository_url: str = None,
        repository_patch: str = None,
        **_,
    ) -> None:
        self.repository_url = repository_url
        self.repository_patch = repository_patch
        self.remotes = [_FakeRepositoryRemote(), _FakeRepositoryRemote()]


class _FakeRepositoryRemote:
    def fetch(self: "_FakeRepositoryRemote") -> None:
        print("Would have fetched the repository")
