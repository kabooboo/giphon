import os

import git


def handle_project(
    root_path,
    project,
    fetch,
    logger,
):

    repo_url = project.ssh_url_to_repo
    repo_path = os.path.join(root_path, project.path_with_namespace)

    if not os.path.isdir(repo_path):
        while "Trying to clone the repo":
            try:
                repo = git.Repo.clone_from(
                    repo_url, repo_path, no_single_branch=True
                )
                break
            except git.exc.GitCommandError as e:
                if e.status == 128:
                    logger.warning(e, exc_info=True)
                    return
                else:
                    raise e

    else:
        if fetch:
            repo = git.Repo(repo_path)
            _fetch_repository(repo)


def _fetch_repository(repo):
    for remote in repo.remotes:
        remote.fetch()
