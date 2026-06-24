import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_HTML = ROOT / "skills" / "building-feature-wikis" / "scripts" / "build_html.py"
MANIFEST = ROOT / "skills" / "building-feature-wikis" / "scripts" / "manifest.py"


class ScriptTests(unittest.TestCase):
    def run_script(self, script, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_build_html_is_self_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            out = tmp_path / "site"
            docs.mkdir()
            (docs / "alpha.md").write_text(
                "<!-- feature-wiki-id: PROJ-1 -->\n"
                "<!-- group: Overview -->\n"
                "# Alpha Feature\n"
                "**Tickets:** PROJ-1\n\n"
                "This is a *small* feature with `code` and [docs](https://example.com).\n",
                encoding="utf-8",
            )

            result = self.run_script(BUILD_HTML, "--docs", str(docs), "--out", str(out), "--title", "Wiki")
            self.assertIn("Built wiki: 1 docs", result.stdout)

            index_html = (out / "index.html").read_text(encoding="utf-8")
            content_js = (out / "content.js").read_text(encoding="utf-8")
            self.assertIn("function render(md)", index_html)
            self.assertNotIn("cdnjs.cloudflare.com", index_html)
            self.assertNotIn("marked.min.js", index_html)
            self.assertNotIn("highlight.min.js", index_html)
            self.assertIn("window.WIKI =", content_js)

    def test_manifest_diff_record_and_rehash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            features = tmp_path / "features.json"
            manifest = tmp_path / "manifest.json"
            features.write_text(
                json.dumps(
                    {
                        "features": [
                            {
                                "slug": "alpha",
                                "fwId": "PROJ-1",
                                "sourceHash": "abc123",
                                "commits": [{"hash": "c1"}],
                            }
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            diff1 = self.run_script(MANIFEST, "diff", str(features), "--manifest", str(manifest))
            self.assertIn("NEW", diff1.stdout)

            record = self.run_script(
                MANIFEST,
                "record",
                "alpha",
                "--fw-id",
                "PROJ-1",
                "--provider",
                "confluence",
                "--page-id",
                "42",
                "--url",
                "https://example.com/page/42",
                "--hash",
                "abc123",
                "--manifest",
                str(manifest),
            )
            self.assertIn("recorded confluence:PROJ-1", record.stdout)

            diff2 = self.run_script(MANIFEST, "diff", str(features), "--manifest", str(manifest))
            self.assertIn("UNCHANGED", diff2.stdout)
            self.assertIn("existing: confluence", diff2.stdout)

            data = json.loads(features.read_text(encoding="utf-8"))
            data["features"][0]["commits"].append({"hash": "c2"})
            features.write_text(json.dumps(data, indent=2), encoding="utf-8")
            rehash = self.run_script(MANIFEST, "rehash", str(features))
            self.assertIn("rehashed 1 features", rehash.stdout)

            rehashed = json.loads(features.read_text(encoding="utf-8"))
            self.assertNotEqual(rehashed["features"][0]["sourceHash"], "abc123")


if __name__ == "__main__":
    unittest.main()
