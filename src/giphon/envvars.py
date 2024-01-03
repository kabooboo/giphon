import re
import sys
from pathlib import Path
from urllib.parse import unquote_plus

from typer import Argument, Option

REGEX_SPECIAL_CHARACTERS = (
    "\\.+?^$()[]{}|"  # NOTE: backslash needs to go first as it escapes others
)


def source(
    environment: str = Argument(
        "...",
        help="The target environment to load variables from.",
    ),
    path: Path = Option(
        Path("."),
        help="The path to load the environment variables from.",
    ),
) -> None:
    """
    Print sourceable exports of environment, with upwards recursion.
    """

    current_path = path.resolve()

    parent_pile = [current_path]

    while current_path != Path("/"):
        current_path = current_path.parent
        parent_pile.append(current_path)

    try:
        while True:
            _source_specific_path(
                environment=environment, path=parent_pile.pop()
            )

    except IndexError:
        return


def _source_specific_path(environment: str, path: Path) -> None:
    """
    Print sourceable exports of environment, for a given directory.
    """

    variables_path = path / Path(".gitlab/.env")
    env_paths = [path for path in variables_path.glob("*") if path.is_file()]

    for env_path in env_paths:
        try:
            (env_type, env_name, env_escaped_scope) = env_path.name.split(":")
        except ValueError:
            print(f"Error: badly formatted file `{env_path}`", file=sys.stderr)

            continue

        env_scope = unquote_plus(env_escaped_scope)

        if not _match_environment_to_scope(
            environment=environment, scope=env_scope
        ):
            continue

        if env_type == "file":
            value = str(env_path.resolve())

        elif env_type == "env_var":
            with open(env_path) as f:
                value = f.read()

        else:
            raise NotImplementedError(f"Unsupported variable type {env_type}")

        print(f"export {env_name}='{value}'")


def _match_environment_to_scope(environment: str, scope: str) -> bool:
    """
    Check if a given environment string matches a given scope wildcard.

    Allowed wildcards are "*".

    Args:
        environment (string): The environment to match
        scope (string): The target scope
    """
    scope_regex = scope

    for char in REGEX_SPECIAL_CHARACTERS:
        scope_regex = scope_regex.replace(char, rf"\{char}")

    scope_regex = scope_regex.replace("*", ".*")

    return bool(re.match(scope_regex, environment))
