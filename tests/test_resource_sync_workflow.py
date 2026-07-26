"""Contract tests for the shared child Panopticon resource-sync workflow."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "shared-child-resource-sync.yml"


class TestSharedChildResourceSyncWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_reusable_contract_has_only_explicit_instance_read_secret(self):
        self.assertIn("workflow_call:", self.text)
        self.assertIn("instance_token:", self.text)
        self.assertIn("required: true", self.text)
        self.assertNotIn("secrets: inherit", self.text)
        self.assertIn("GH_TOKEN: ${{ secrets.instance_token }}", self.text)
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.text)

    def test_non_default_branch_fails_before_instance_token_is_mapped(self):
        gate = self.text.index("Require the child default branch")
        token_mapping = self.text.index("GH_TOKEN: ${{ secrets.instance_token }}")
        self.assertLess(gate, token_mapping)
        self.assertIn('CURRENT_REF: ${{ github.ref }}', self.text)
        self.assertIn('DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}', self.text)
        self.assertIn('"refs/heads/$DEFAULT_BRANCH"', self.text)

    def test_uses_existing_sync_and_skips_pr_when_current(self):
        self.assertIn("python3 -m panopticon.sync", self.text)
        self.assertIn("git diff --quiet", self.text)
        self.assertIn("changed=false", self.text)
        self.assertIn("steps.resources.outputs.changed == 'false'", self.text)
        self.assertIn("no branch or pull request was created", self.text)

    def test_changed_resources_update_only_an_open_automation_owned_pr(self):
        self.assertIn('branch="panopticon/resource-sync"', self.text)
        self.assertIn("git push --force-with-lease", self.text)
        self.assertIn(
            'gh pr list --head "$branch" --base "$DEFAULT_BRANCH" --state open', self.text
        )
        self.assertIn("'.[0].url // empty'", self.text)
        self.assertNotIn('gh pr view "$branch"', self.text)
        self.assertIn("gh pr create --base", self.text)
        self.assertIn("pull-requests: write", self.text)
        self.assertIn("Review and merge this automation-owned pull request", self.text)


if __name__ == "__main__":
    unittest.main()
