"""Real-git integration tests for sync-from-template.yml's runtime merge attributes.

The tests cover two distinct classifications written to ``.git/info/attributes`` before a merge:
the template-declared, instance-owned generated org diagram and org-declared ``protected_paths``.
The point is Git's real add/add, modify/modify, unrelated-history, and one-sided-add behavior, so
the repository operations intentionally use subprocesses rather than mocks.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SYNC_WORKFLOW = ROOT / ".github" / "workflows" / "sync-from-template.yml"


def _git(args, cwd, check=True):
    result = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=30
    )
    if check and result.returncode != 0:
        raise AssertionError(f"git {args} failed in {cwd}:\n{result.stdout}\n{result.stderr}")
    return result


def _init_repo(path, branch="main"):
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q", "-b", branch], path)
    _git(["config", "user.email", "a@b.c"], path)
    _git(["config", "user.name", "a"], path)


def _commit_all(path, message):
    _git(["add", "-A"], path)
    _git(["commit", "-q", "-m", message], path)


GENERATED_PATHS = ("docs/architecture.md",)


class TestTemplateSyncAuthentication(unittest.TestCase):
    def test_default_token_fallback_prevents_empty_checkout_token(self):
        text = SYNC_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "token: ${{ secrets.PANOPTICON_INSTANCE_TOKEN || github.token }}", text
        )
        self.assertIn("Record template-sync authentication", text)
        self.assertIn("PANOPTICON_SYNC_START_SHA", text)

    def test_workflow_changes_are_blocked_without_instance_token_before_push(self):
        text = SYNC_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Validate token before pushing workflow changes", text)
        self.assertIn(
            'git diff --quiet "$PANOPTICON_SYNC_START_SHA" HEAD -- .github/workflows', text
        )
        self.assertIn("PANOPTICON_INSTANCE_TOKEN GitHub-token secret", text)
        self.assertLess(
            text.index("Validate token before pushing workflow changes"), text.index("- name: Push")
        )


def _register_runtime_attributes(instance_root, protected_paths=()):
    """Reproduce the workflow's fixed and dynamic runtime attribute registration."""
    _git(["config", "merge.ours.driver", "true"], instance_root)
    attrs = Path(instance_root) / ".git" / "info" / "attributes"
    attrs.parent.mkdir(parents=True, exist_ok=True)
    attributed_paths = dict.fromkeys((*GENERATED_PATHS, *protected_paths))
    attrs.write_text(
        "".join(f"{path} merge=ours\n" for path in attributed_paths), encoding="utf-8"
    )


class TestRoutineSyncProtection(unittest.TestCase):
    def test_protected_path_survives_when_incoming_also_modifies_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template"
            instance = Path(tmp) / "instance"
            _init_repo(template)
            (template / "skill.md").write_text("template default v1")
            (template / ".gitattributes").write_text("panopticon.diagram.config.json merge=ours\n")
            _commit_all(template, "template initial")

            # Instance clones template history (routine sync assumes a common ancestor), then
            # customizes the protected file.
            _git(["clone", "-q", str(template), str(instance)], tmp)
            _git(["config", "user.email", "a@b.c"], instance)
            _git(["config", "user.name", "a"], instance)
            (instance / "skill.md").write_text("instance custom")
            _commit_all(instance, "instance customization")

            # Template moves on, modifying the same path (the case that hard-aborts a merge if
            # the protection were an uncommitted edit to the *tracked* .gitattributes instead).
            (template / "skill.md").write_text("template default v2")
            _commit_all(template, "template update")

            _git(["remote", "add", "template", str(template)], instance)
            _git(["fetch", "-q", "template", "main"], instance)

            _register_runtime_attributes(instance, ["skill.md"])

            merge = _git(["merge", "template/main", "--no-edit"], instance, check=False)

            self.assertEqual(merge.returncode, 0, merge.stdout + merge.stderr)
            self.assertEqual((instance / "skill.md").read_text(), "instance custom")
            # The tracked .gitattributes is untouched by protected_paths and merges normally —
            # identical on both sides here, so no conflict.
            self.assertEqual(
                (instance / ".gitattributes").read_text(),
                "panopticon.diagram.config.json merge=ours\n",
            )


class TestFirstSyncProtection(unittest.TestCase):
    def test_first_sync_with_no_common_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template"
            instance = Path(tmp) / "instance"
            _init_repo(template)
            (template / "README.md").write_text("template readme")
            _commit_all(template, "template initial")

            # "Use this template" creates unrelated history.
            _init_repo(instance)
            (instance / "skill.md").write_text("instance custom, never in template")
            (instance / "panopticon.config.json").write_text('{"protected_paths": ["skill.md"]}')
            _commit_all(instance, "instance initial")

            _git(["remote", "add", "template", str(template)], instance)
            _git(["fetch", "-q", "template", "main"], instance)

            _register_runtime_attributes(instance, ["skill.md"])

            merge = _git(
                ["merge", "template/main", "--no-edit", "--allow-unrelated-histories", "-X", "theirs"],
                instance, check=False,
            )

            self.assertEqual(merge.returncode, 0, merge.stdout + merge.stderr)
            self.assertEqual((instance / "skill.md").read_text(), "instance custom, never in template")
            self.assertEqual((instance / "README.md").read_text(), "template readme")

    def test_first_sync_same_path_conflict_org_version_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template"
            instance = Path(tmp) / "instance"
            _init_repo(template)
            (template / "skill.md").write_text("template default")
            _commit_all(template, "template initial")

            # Unrelated history, but the same path exists on both sides with different content —
            # a genuine add/add conflict -X theirs would otherwise resolve in the template's favor.
            _init_repo(instance)
            (instance / "skill.md").write_text("org customized before first sync")
            _commit_all(instance, "instance initial")

            _git(["remote", "add", "template", str(template)], instance)
            _git(["fetch", "-q", "template", "main"], instance)

            _register_runtime_attributes(instance, ["skill.md"])

            merge = _git(
                ["merge", "template/main", "--no-edit", "--allow-unrelated-histories", "-X", "theirs"],
                instance, check=False,
            )

            self.assertEqual(merge.returncode, 0, merge.stdout + merge.stderr)
            self.assertEqual((instance / "skill.md").read_text(), "org customized before first sync")


class TestGeneratedOrgDiagramSync(unittest.TestCase):
    def test_routine_sync_both_sides_independently_add_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template"
            instance = Path(tmp) / "instance"
            _init_repo(template)
            (template / "README.md").write_text("shared base")
            _commit_all(template, "shared base")

            _git(["clone", "-q", str(template), str(instance)], tmp)
            _git(["config", "user.email", "a@b.c"], instance)
            _git(["config", "user.name", "a"], instance)

            (instance / "docs").mkdir()
            (instance / "docs" / "architecture.md").write_text("instance generated")
            _commit_all(instance, "instance adds generated diagram")

            (template / "docs").mkdir()
            (template / "docs" / "architecture.md").write_text("template placeholder")
            _commit_all(template, "template adds placeholder")

            _git(["remote", "add", "template", str(template)], instance)
            _git(["fetch", "-q", "template", "main"], instance)
            _register_runtime_attributes(instance)

            merge = _git(["merge", "template/main", "--no-edit"], instance, check=False)

            self.assertEqual(merge.returncode, 0, merge.stdout + merge.stderr)
            self.assertEqual(
                (instance / "docs" / "architecture.md").read_text(), "instance generated"
            )

    def test_routine_sync_both_sides_modify_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template"
            instance = Path(tmp) / "instance"
            _init_repo(template)
            (template / "docs").mkdir()
            (template / "docs" / "architecture.md").write_text("shared placeholder")
            _commit_all(template, "shared placeholder")

            _git(["clone", "-q", str(template), str(instance)], tmp)
            _git(["config", "user.email", "a@b.c"], instance)
            _git(["config", "user.name", "a"], instance)

            (instance / "docs" / "architecture.md").write_text("instance generated")
            _commit_all(instance, "instance generates diagram")
            (template / "docs" / "architecture.md").write_text("template placeholder update")
            _commit_all(template, "template updates placeholder")

            _git(["remote", "add", "template", str(template)], instance)
            _git(["fetch", "-q", "template", "main"], instance)
            _register_runtime_attributes(instance)

            merge = _git(["merge", "template/main", "--no-edit"], instance, check=False)

            self.assertEqual(merge.returncode, 0, merge.stdout + merge.stderr)
            self.assertEqual(
                (instance / "docs" / "architecture.md").read_text(), "instance generated"
            )

    def test_first_sync_unrelated_histories_preserves_instance_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template"
            instance = Path(tmp) / "instance"
            _init_repo(template)
            (template / "docs").mkdir()
            (template / "docs" / "architecture.md").write_text("template placeholder")
            _commit_all(template, "template initial")

            _init_repo(instance)
            (instance / "docs").mkdir()
            (instance / "docs" / "architecture.md").write_text("instance generated")
            _commit_all(instance, "instance initial")

            _git(["remote", "add", "template", str(template)], instance)
            _git(["fetch", "-q", "template", "main"], instance)
            _register_runtime_attributes(instance)

            merge = _git(
                ["merge", "template/main", "--no-edit", "--allow-unrelated-histories", "-X", "theirs"],
                instance,
                check=False,
            )

            self.assertEqual(merge.returncode, 0, merge.stdout + merge.stderr)
            self.assertEqual(
                (instance / "docs" / "architecture.md").read_text(), "instance generated"
            )

    def test_template_placeholder_is_installed_when_instance_lacks_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template"
            instance = Path(tmp) / "instance"
            _init_repo(template)
            (template / "README.md").write_text("shared base")
            _commit_all(template, "shared base")

            _git(["clone", "-q", str(template), str(instance)], tmp)
            _git(["config", "user.email", "a@b.c"], instance)
            _git(["config", "user.name", "a"], instance)

            (template / "docs").mkdir()
            (template / "docs" / "architecture.md").write_text("template placeholder")
            _commit_all(template, "template adds placeholder")

            _git(["remote", "add", "template", str(template)], instance)
            _git(["fetch", "-q", "template", "main"], instance)
            _register_runtime_attributes(instance)

            merge = _git(["merge", "template/main", "--no-edit"], instance, check=False)

            self.assertEqual(merge.returncode, 0, merge.stdout + merge.stderr)
            self.assertEqual(
                (instance / "docs" / "architecture.md").read_text(), "template placeholder"
            )


if __name__ == "__main__":
    unittest.main()
