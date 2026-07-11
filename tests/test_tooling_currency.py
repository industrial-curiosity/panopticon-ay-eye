"""Advisory-only tooling-currency PR check (panopticon/tooling_currency.py): ref-resolution,
skills/tooling drift-diff logic, and warning-format output. All subprocess/filesystem stubbed."""

import contextlib
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from panopticon.tooling_currency import (
    _diff_files,
    _panopticon_skill_files,
    _tooling_module_files,
    check_skills_and_tooling_drift,
    check_workflow_ref,
    main,
)


def _fake_runner(responses):
    """responses: dict mapping tuple(args) -> (returncode, stdout)."""
    class Result:
        def __init__(self, returncode, stdout):
            self.returncode = returncode
            self.stdout = stdout

    def runner(args, **kwargs):
        key = tuple(args)
        if key not in responses:
            raise AssertionError(f"unexpected command: {args}")
        returncode, stdout = responses[key]
        return Result(returncode, stdout)

    return runner


class TestCheckWorkflowRef(unittest.TestCase):
    def _write_caller_workflow(self, child_root, ref):
        workflows = Path(child_root) / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "panopticon-pr.yml").write_text(
            f"jobs:\n  panopticon:\n    uses: acme/instance/.github/workflows/panopticon-pr.yml@{ref}\n",
            encoding="utf-8",
        )

    def test_aligned_ref_yields_no_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_caller_workflow(tmp, "main")
            runner = _fake_runner({
                ("git", "-C", ".panopticon-instance", "ls-remote", "origin", "main"): (0, "abc123\trefs/heads/main\n"),
                ("git", "-C", ".panopticon-instance", "rev-parse", "HEAD"): (0, "abc123\n"),
            })
            result = check_workflow_ref(tmp, ".panopticon-instance", runner=runner)
        self.assertIsNone(result)

    def test_behind_ref_yields_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_caller_workflow(tmp, "v1")
            runner = _fake_runner({
                ("git", "-C", ".panopticon-instance", "ls-remote", "origin", "v1"): (0, "oldsha1234567\trefs/tags/v1\n"),
                ("git", "-C", ".panopticon-instance", "rev-parse", "HEAD"): (0, "newsha7654321\n"),
            })
            result = check_workflow_ref(tmp, ".panopticon-instance", runner=runner)
        self.assertIn("v1", result)
        self.assertIn("no longer matches", result)

    def test_deleted_ref_yields_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_caller_workflow(tmp, "deleted-tag")
            runner = _fake_runner({
                ("git", "-C", ".panopticon-instance", "ls-remote", "origin", "deleted-tag"): (0, ""),
            })
            result = check_workflow_ref(tmp, ".panopticon-instance", runner=runner)
        self.assertIn("deleted-tag", result)
        self.assertIn("no longer resolves", result)

    def test_unparseable_caller_workflow_yields_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = check_workflow_ref(tmp, ".panopticon-instance", runner=_fake_runner({}))
        self.assertIn("could not determine", result)


class TestPanopticonSkillFiles(unittest.TestCase):
    def test_collects_files_under_panopticon_prefixed_dirs_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "panopticon-foo").mkdir()
            (root / "panopticon-foo" / "SKILL.md").write_text("a")
            (root / "openspec-bar").mkdir()
            (root / "openspec-bar" / "SKILL.md").write_text("b")
            files = _panopticon_skill_files(root)
        self.assertEqual(set(files), {Path("panopticon-foo/SKILL.md")})

    def test_missing_root_returns_empty(self):
        self.assertEqual(_panopticon_skill_files("/no/such/dir"), {})


class TestToolingModuleFiles(unittest.TestCase):
    def test_only_existing_modules_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "panopticon").mkdir()
            (root / "panopticon" / "docs.py").write_text("x")
            files = _tooling_module_files(tmp, ("docs.py", "index.py"))
        self.assertEqual(set(files), {Path("panopticon/docs.py")})


class TestDiffFiles(unittest.TestCase):
    def test_identical_content_yields_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.py"
            b = Path(tmp) / "b.py"
            a.write_text("same")
            b.write_text("same")
            findings = _diff_files({Path("x.py"): a}, {Path("x.py"): b})
        self.assertEqual(findings, [])

    def test_differing_content_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.py"
            b = Path(tmp) / "b.py"
            a.write_text("old")
            b.write_text("new")
            findings = _diff_files({Path("panopticon/docs.py"): a}, {Path("panopticon/docs.py"): b})
        self.assertEqual(len(findings), 1)
        self.assertIn("panopticon/docs.py", findings[0])
        self.assertIn("out of date", findings[0])

    def test_missing_from_child_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.py"
            a.write_text("x")
            findings = _diff_files({Path("panopticon-new/SKILL.md"): a}, {})
        self.assertEqual(len(findings), 1)
        self.assertIn("panopticon-new/SKILL.md", findings[0])
        self.assertIn("missing from this repo", findings[0])

    def test_extra_in_child_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / "b.py"
            b.write_text("x")
            findings = _diff_files({}, {Path("panopticon-extra/SKILL.md"): b})
        self.assertEqual(len(findings), 1)
        self.assertIn("panopticon-extra/SKILL.md", findings[0])
        self.assertIn("not in the instance", findings[0])


class TestCheckSkillsAndToolingDrift(unittest.TestCase):
    def test_matching_trees_yield_no_findings(self):
        with tempfile.TemporaryDirectory() as instance_root, tempfile.TemporaryDirectory() as child_root:
            (Path(instance_root) / ".agents" / "skills" / "panopticon-foo").mkdir(parents=True)
            (Path(instance_root) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md").write_text("v1")
            (Path(child_root) / ".agents" / "skills" / "panopticon-foo").mkdir(parents=True)
            (Path(child_root) / ".agents" / "skills" / "panopticon-foo" / "SKILL.md").write_text("v1")

            (Path(instance_root) / "panopticon").mkdir()
            (Path(child_root) / "panopticon").mkdir()
            for name in ("__init__.py", "config.py", "docs.py", "index.py", "init_repo.py", "sync.py"):
                (Path(instance_root) / "panopticon" / name).write_text(name)
                (Path(child_root) / "panopticon" / name).write_text(name)

            findings = check_skills_and_tooling_drift(child_root, instance_root)
        self.assertEqual(findings, [])

    def test_drifted_tooling_module_reported(self):
        with tempfile.TemporaryDirectory() as instance_root, tempfile.TemporaryDirectory() as child_root:
            (Path(instance_root) / "panopticon").mkdir()
            (Path(child_root) / "panopticon").mkdir()
            (Path(instance_root) / "panopticon" / "docs.py").write_text("new")
            (Path(child_root) / "panopticon" / "docs.py").write_text("old")

            findings = check_skills_and_tooling_drift(child_root, instance_root)
        self.assertTrue(any("panopticon/docs.py" in f for f in findings))

    def test_missing_skill_reported(self):
        with tempfile.TemporaryDirectory() as instance_root, tempfile.TemporaryDirectory() as child_root:
            (Path(instance_root) / ".agents" / "skills" / "panopticon-new").mkdir(parents=True)
            (Path(instance_root) / ".agents" / "skills" / "panopticon-new" / "SKILL.md").write_text("x")

            findings = check_skills_and_tooling_drift(child_root, instance_root)
        self.assertTrue(any("panopticon-new" in f for f in findings))


class TestMain(unittest.TestCase):
    """Exercises main() end-to-end, including the real `git ls-remote`/`git rev-parse` calls
    check_workflow_ref makes by default — a real git repo (its own remote, via a local filesystem
    path, no network) rather than a stubbed runner, mirroring this change's real-git-repo
    convention (design.md's protected-config spike, group 6.2)."""

    def _init_git_repo(self, path):
        subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "a@b.c"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "a"], check=True)
        (Path(path) / "README.md").write_text("x")
        subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)
        subprocess.run(["git", "-C", str(path), "remote", "add", "origin", str(path)], check=True)

    def _write_caller_workflow(self, child_root, ref):
        workflows = Path(child_root) / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "panopticon-pr.yml").write_text(
            f"jobs:\n  panopticon:\n    uses: acme/instance/.github/workflows/panopticon-pr.yml@{ref}\n",
            encoding="utf-8",
        )

    def test_clean_repo_prints_no_warnings_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as instance_root, tempfile.TemporaryDirectory() as child_root:
            self._init_git_repo(instance_root)
            self._write_caller_workflow(child_root, "main")
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--child-root", child_root, "--instance-root", instance_root])
            self.assertEqual(code, 0)
            self.assertNotIn("::warning::", out.getvalue())

    def test_findings_printed_as_warnings_and_still_exits_zero(self):
        with tempfile.TemporaryDirectory() as instance_root, tempfile.TemporaryDirectory() as child_root:
            self._init_git_repo(instance_root)
            self._write_caller_workflow(child_root, "main")
            (Path(instance_root) / ".agents" / "skills" / "panopticon-new").mkdir(parents=True)
            (Path(instance_root) / ".agents" / "skills" / "panopticon-new" / "SKILL.md").write_text("x")
            out = StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--child-root", child_root, "--instance-root", instance_root])
            self.assertEqual(code, 0)
            self.assertIn("::warning::", out.getvalue())
            self.assertIn("panopticon-new", out.getvalue())


if __name__ == "__main__":
    unittest.main()
