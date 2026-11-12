"""Tests for Hardware Knowledge Hub. Standard library only:

    python3 -m unittest discover -s tests -v
"""
import http.client
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "hub_package" / "template"
sys.path.insert(0, str(ROOT))

import hub_package  # noqa: E402

WORK = None      # a temporary directory for the whole run
PROJECT = None   # a fresh project created by `hardware-knowledge-hub init`
kb = None        # that project's kb.py, so tests never write into the repository


def setUpModule():
    global WORK, PROJECT, kb
    WORK = Path(tempfile.mkdtemp(prefix="hub-test-")).resolve()
    PROJECT = WORK / "project"
    with mock.patch.object(sys, "argv", ["hardware-knowledge-hub", "init", str(PROJECT)]), \
            mock.patch("builtins.print"):
        hub_package.main()
    spec = importlib.util.spec_from_file_location("project_kb", PROJECT / "hardware" / "knowledge" / "kb.py")
    kb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kb)


def tearDownModule():
    shutil.rmtree(WORK, ignore_errors=True)


class InitTest(unittest.TestCase):
    def test_new_project_has_notes_editor_and_prints(self):
        for path in ("AGENTS.md", "CLAUDE.md", "hardware/CLAUDE.md", "hardware/knowledge/knowledge.json",
                     "hardware/knowledge/ui/index.html", "hardware/cad/parameters.json"):
            self.assertTrue((PROJECT / path).is_file(), path)
        self.assertTrue(list((PROJECT / "hardware" / "print").glob("*.stl")))

    def test_refuses_an_existing_directory(self):
        with mock.patch.object(sys, "argv", ["hardware-knowledge-hub", "init", str(PROJECT)]), \
                mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            hub_package.main()

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_node_cli_creates_the_same_project(self):
        target = WORK / "from-node"
        subprocess.run(["node", str(ROOT / "cli.cjs"), "init", str(target)], check=True, capture_output=True)
        self.assertEqual((target / "hardware" / "knowledge" / "knowledge.json").read_bytes(),
                         (TEMPLATE / "hardware" / "knowledge" / "knowledge.json").read_bytes())


class RenderTest(unittest.TestCase):
    def test_table_escapes_pipes_and_pads_short_rows(self):
        lines = kb.table(["Part", "Note"], [["a|b", "two\nlines"], ["only one"]])
        self.assertEqual(lines[0], "| Part | Note |")
        self.assertEqual(lines[2], "| a\\|b | two lines |")
        self.assertEqual(lines[3], "| only one |  |")

    def test_empty_table_says_so(self):
        self.assertEqual(kb.table(["Part"], []), ["(none yet)", ""])

    def test_each_section_type(self):
        text = kb.render({"sections": [
            {"title": "Rules", "type": "list", "items": ["first", "second"]},
            {"title": "Parts", "type": "table", "intro": "On hand.", "columns": ["Part"], "rows": [["Pi 5"]]},
            {"title": "Open questions", "text": "None."},
        ]})
        self.assertTrue(text.startswith("# Hardware knowledge\n"))
        self.assertIn("## Rules\n\n- first\n- second\n", text)
        self.assertIn("## Parts\n\nOn hand.\n\n| Part |\n|---|\n| Pi 5 |\n", text)
        self.assertTrue(text.endswith("## Open questions\n\nNone.\n"))

    def test_generated_notes_match_the_data(self):
        """The same check as `kb.py check`: hardware/CLAUDE.md must be regenerated after editing the JSON."""
        self.assertEqual(kb.OUT.read_text(), kb.render(kb.load()))


class ParametersTest(unittest.TestCase):
    def setUp(self):
        self.before = kb.PARAMS.read_text()
        self.addCleanup(kb.PARAMS.write_text, self.before)
        self.key = json.loads(self.before)["parameters"][0]["key"]

    def test_saves_a_number_and_keeps_the_label(self):
        kb.save_params({"values": {self.key: 12.5}})
        first = json.loads(kb.PARAMS.read_text())["parameters"][0]
        self.assertEqual(first["value"], 12.5)
        self.assertEqual(first["label"], json.loads(self.before)["parameters"][0]["label"])

    def test_rejects_unknown_keys_and_non_numbers(self):
        for values in ({"no_such_dimension": 1}, {self.key: "12"}, {self.key: True}):
            with self.assertRaises(ValueError):
                kb.save_params({"values": values})
        self.assertEqual(kb.PARAMS.read_text(), self.before)


class OpenModelTest(unittest.TestCase):
    def open(self, name, app, returncode=0):
        done = mock.Mock(returncode=returncode, stderr="")
        with mock.patch.object(kb.sys, "platform", "darwin"), \
                mock.patch.object(kb.subprocess, "run", return_value=done) as run:
            return kb.open_model(name, app), run

    def test_slicers_get_the_plate_when_there_is_one(self):
        result, run = self.open("camera_plate.stl", "bambu")
        self.assertEqual(result, {"opened": "camera_plate.3mf"})
        self.assertEqual(run.call_args.args[0][:3], ["open", "-a", "BambuStudio"])

    def test_freecad_gets_the_step_file(self):
        self.assertEqual(self.open("camera_cap.stl", "freecad")[0], {"opened": "camera_cap.step"})

    def test_falls_back_to_the_stl(self):
        self.assertEqual(self.open("rear_box_lid.stl", "prusa")[0], {"opened": "rear_box_lid.stl"})

    def test_rejects_unknown_apps_and_files_outside_print(self):
        for name, app in (("camera_cap.stl", "calculator"), ("../knowledge/kb.py", "bambu"),
                          ("missing.stl", "bambu"), ("camera_cap.step", "bambu")):
            with self.assertRaises(ValueError):
                self.open(name, app)

    def test_reports_an_app_that_is_not_installed(self):
        with self.assertRaisesRegex(ValueError, "Could not open OrcaSlicer"):
            self.open("camera_cap.stl", "orca", returncode=1)

    def test_other_systems_get_a_clear_message(self):
        with mock.patch.object(kb.sys, "platform", "linux"), self.assertRaisesRegex(ValueError, "macOS"):
            kb.open_model("camera_cap.stl", "bambu")


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), kb.Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        patcher = mock.patch.object(kb, "PORT", self.port)
        patcher.start()
        self.addCleanup(patcher.stop)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        self.addCleanup(connection.close)
        payload = None if body is None else json.dumps(body)
        connection.request(method, path, payload, headers or {})
        response = connection.getresponse()
        return response.status, response.read()

    def test_serves_the_editor_and_the_data(self):
        status, page = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<title>Hardware knowledge</title>", page)
        status, data = self.request("GET", "/api/knowledge")
        self.assertEqual(json.loads(data), kb.load())
        status, models = self.request("GET", "/api/models")
        self.assertEqual({m["name"] for m in json.loads(models)}, {p.name for p in kb.PRINT.glob("*.stl")})

    def test_serves_only_its_own_files(self):
        for path in ("/../kb.py", "/stl/../knowledge/knowledge.json", "/stl/camera_cap.step",
                     "/api/preview/../../parameters", "/nothing.html"):
            self.assertEqual(self.request("GET", path)[0], 404, path)

    def test_render_previews_without_saving(self):
        before = kb.OUT.read_text()
        status, body = self.request("POST", "/api/render", {"sections": [{"title": "Draft", "text": "Not saved."}]})
        self.assertEqual(status, 200)
        self.assertIn("## Draft", json.loads(body)["markdown"])
        self.assertEqual(kb.OUT.read_text(), before)

    def test_save_writes_the_json_and_the_notes(self):
        original = kb.load()
        self.addCleanup(kb.save, original)
        edited = json.loads(json.dumps(original))
        edited["sections"].append({"title": "Added by a test", "text": "Hello."})
        status, _ = self.request("POST", "/api/save", edited)
        self.assertEqual(status, 200)
        self.assertEqual(kb.load(), edited)
        self.assertIn("## Added by a test", kb.OUT.read_text())

    def test_bad_data_is_a_400_not_a_crash(self):
        self.assertEqual(self.request("POST", "/api/save", {"sections": [{"type": "table"}]})[0], 400)

    def test_other_websites_cannot_write(self):
        status, _ = self.request("POST", "/api/save", kb.load(), {"Origin": "https://example.com"})
        self.assertEqual(status, 403)

    def test_read_only_copy_refuses_changes(self):
        with mock.patch.object(kb, "READONLY", True):
            self.assertEqual(self.request("POST", "/api/save", kb.load())[0], 403)
            self.assertEqual(self.request("POST", "/api/render", kb.load())[0], 200)
            self.assertEqual(json.loads(self.request("GET", "/api/config")[1]), {"readonly": True})


class DemoTest(unittest.TestCase):
    """docs/demo is the static copy GitHub Pages serves. It is built from the template and must not drift from it."""

    @classmethod
    def setUpClass(cls):
        cls.demo = WORK / "demo"
        subprocess.run([sys.executable, str(PROJECT / "hardware" / "knowledge" / "build_demo.py"), str(cls.demo)],
                       check=True, capture_output=True)

    def test_demo_is_read_only_and_complete(self):
        self.assertEqual(json.loads((self.demo / "api" / "config").read_text()), {"readonly": True})
        self.assertIn("Bike Logger demo", (self.demo / "index.html").read_text())
        models = {m["name"] for m in json.loads((self.demo / "api" / "models").read_text())}
        self.assertEqual(models, {p.name for p in (self.demo / "stl").iterdir()})

    def test_refuses_to_overwrite(self):
        result = subprocess.run([sys.executable, str(PROJECT / "hardware" / "knowledge" / "build_demo.py"),
                                 str(self.demo)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("empty output directory", result.stderr)

    def test_committed_demo_matches_the_template(self):
        published = ROOT / "docs" / "demo"
        files = lambda base: {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}  # noqa: E731
        self.assertEqual(files(published), files(self.demo), "rebuild docs/demo (see CONTRIBUTING.md)")
        stale = [name for name in sorted(files(published))
                 if name != "api/models"  # holds file times, which differ on every build
                 and (published / name).read_bytes() != (self.demo / name).read_bytes()]
        self.assertEqual(stale, [], "rebuild docs/demo (see CONTRIBUTING.md)")


class PackagingTest(unittest.TestCase):
    def test_pypi_and_npm_versions_agree(self):
        python = re.search(r'^version = "(.+)"$', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
        node = json.loads((ROOT / "package.json").read_text())["version"]
        self.assertEqual(python, node)

    def test_template_has_no_caches_or_private_files(self):
        unwanted = [p.relative_to(TEMPLATE).as_posix() for p in TEMPLATE.rglob("*")
                    if p.name in ("__pycache__", ".DS_Store", ".env") or p.suffix == ".pyc"]
        self.assertEqual(unwanted, [])


if __name__ == "__main__":
    unittest.main()
