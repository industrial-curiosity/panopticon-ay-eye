"""Org-diagram link script (architecture-diagrams capability: "Org-diagram link script"): prints a
resolvable, clickable GitHub URL to this repo's section of the org-wide architecture diagram.

Complements the relative link embedded in this repo's own `## Architecture diagram` section
(panopticon-doc-generation): that embedded link is authored for its *post-merge* location and only
resolves once this repo's docs have been merged into the instance repo. This script instead gives a
developer sitting in the child repo's own checkout, before any merge, an immediately clickable link
to the current org-wide picture — reading only local config, no network call, no instance-repo
clone, no `PYTHONPATH` setup.
"""

import sys

from .config import ConfigError, load_repo_config


def build_link(repo_config):
    """Build the org-diagram deep link from an already-loaded repo config dict. Raises ConfigError
    when `instance_default_branch` is missing — never guessed (see repo-initialization's "Recorded
    instance_default_branch is resolved deterministically, never guessed")."""
    branch = repo_config.get("instance_default_branch")
    if not branch:
        raise ConfigError(
            "panopticon/config.json has no 'instance_default_branch' — re-run "
            "'python3 -m panopticon.init_repo' with the gh CLI installed and authenticated to "
            "populate it."
        )
    return (
        f"https://github.com/{repo_config['instance']}/blob/{branch}"
        f"/docs/architecture.md#{repo_config['repo']}"
    )


def main(argv=None, child_root="."):
    repo_config = load_repo_config(child_root)
    if repo_config is None:
        print("error: this repo is not Panopticon-initialized (panopticon/config.json missing)")
        return 1
    try:
        print(build_link(repo_config))
    except ConfigError as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
