import importlib.util
import json
import subprocess
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MINE_HISTORY = ROOT / "skills" / "building-feature-wikis" / "scripts" / "mine_history.py"

spec = importlib.util.spec_from_file_location("mine_history", MINE_HISTORY)
mine_history = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mine_history)


class MineHistoryTests(unittest.TestCase):
    def run_mine_history(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(MINE_HISTORY), *args],
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_ticket_sort_key_prefers_lowest_number(self):
        keys = ["PROJ-12", "PROJ-2", "PROJ-1", "jira:ABC-10", "jira:ABC-3"]
        self.assertEqual(
            sorted(keys, key=mine_history.ticket_sort_key),
            ["PROJ-1", "PROJ-2", "PROJ-12", "jira:ABC-3", "jira:ABC-10"],
        )

    def test_clean_branch_removes_common_prefixes(self):
        self.assertEqual(mine_history.clean_branch("feature/login-flow"), "login-flow")
        self.assertEqual(mine_history.clean_branch("release/1.2.3"), "1.2.3")
        self.assertEqual(mine_history.clean_branch("docs/readme"), "docs/readme")

    def test_assign_key_prefers_ticket_over_scope(self):
        ticket_re = re.compile(r"[A-Z][A-Z0-9]+-\d+")
        commit = {
            "hash": "c1",
            "subject": "feat(auth): PROJ-9 add session cookie",
            "body": "",
        }
        self.assertEqual(
            mine_history.assign_key(commit, ticket_re, "ticket", {}),
            ("PROJ-9", "ticket"),
        )

    def test_assign_key_falls_back_to_scope(self):
        ticket_re = re.compile(r"[A-Z][A-Z0-9]+-\d+")
        commit = {
            "hash": "c2",
            "subject": "feat(auth): add session cookie",
            "body": "",
        }
        self.assertEqual(
            mine_history.assign_key(commit, ticket_re, "ticket", {}),
            ("auth", "scope"),
        )

    def test_best_title_ignores_merge_subjects(self):
        commits = [
            {"subject": "Merge branch 'feature/login'"},
            {"subject": "chore: bump deps"},
            {"subject": "feat(auth): add session cookie"},
        ]
        self.assertEqual(
            mine_history.best_title(commits, "auth"),
            "feat(auth): add session cookie",
        )

    def test_branch_grouping_recovers_from_merge_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.run_git(repo, "init")
            self.run_git(repo, "config", "user.email", "root@example.com")
            self.run_git(repo, "config", "user.name", "Root")
            base_branch = self.run_git(repo, "symbolic-ref", "--short", "HEAD").stdout.strip()

            (repo / "base.txt").write_text("base\n", encoding="utf-8")
            self.run_git(repo, "add", "base.txt")
            self.run_git(repo, "commit", "-m", "chore: init")

            self.run_git(repo, "checkout", "-b", "feature/login")
            self.run_git(repo, "config", "user.email", "dev@example.com")
            self.run_git(repo, "config", "user.name", "Dev")
            (repo / "login.txt").write_text("login\n", encoding="utf-8")
            self.run_git(repo, "add", "login.txt")
            self.run_git(repo, "commit", "-m", "feat(auth): add login flow")

            self.run_git(repo, "checkout", base_branch)
            self.run_git(repo, "merge", "--no-ff", "feature/login", "-m", "Merge branch 'feature/login'")

            out = repo / "features.json"
            result = self.run_mine_history(
                "--repo",
                str(repo),
                "--author",
                "dev@example.com",
                "--group-by",
                "branch",
                "--out",
                str(out),
            )
            self.assertIn("Wrote 1 features", result.stdout)

            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["featureCount"], 1)
            feature = payload["features"][0]
            self.assertEqual(feature["kind"], "branch")
            self.assertEqual(feature["fwId"], "slug:login")
            self.assertEqual(feature["branches"], ["login"])

    def run_git(self, cwd, *args):
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
