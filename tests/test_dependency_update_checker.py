import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "bin" / "dependency_update_checker.py"
SPEC = importlib.util.spec_from_file_location("dependency_update_checker", MODULE_PATH)
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checker)


class DependencyUpdateCheckerTests(unittest.TestCase):
    def write_temp_deps(self, content: str) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".gradle", delete=False) as handle:
            handle.write(content)
            deps_file = handle.name

        self.addCleanup(Path(deps_file).unlink, missing_ok=True)
        return deps_file

    def test_select_metadata_candidate_ignores_pre_suffix_versions(self) -> None:
        candidate = checker.select_metadata_candidate(
            "2.2.10-GTNH-pre",
            "2.2.10-GTNH-pre",
            ["2.2.9-GTNH", "2.2.10-GTNH-pre"],
        )

        self.assertEqual(candidate, "2.2.9-GTNH")

    def test_scan_dependencies_does_not_downgrade_current_pre_version(self) -> None:
        deps_file = self.write_temp_deps(
            'implementation "com.github.GTNewHorizons:Baubles-Expanded:2.2.10-GTNH-pre:dev"\n'
        )

        with mock.patch.object(
            checker,
            "fetch_latest_from_metadata",
            return_value=(
                "2.2.9-GTNH",
                "https://example.invalid/maven-metadata.xml",
                ["2.2.9-GTNH", "2.2.10-GTNH-pre"],
            ),
        ):
            state = checker.scan_dependencies(deps_file, timeout_seconds=0.01)

        self.assertEqual(state["candidates"], [])

    def test_scan_dependencies_keeps_latest_stable_when_newest_is_pre(self) -> None:
        deps_file = self.write_temp_deps(
            'implementation "com.github.GTNewHorizons:Baubles-Expanded:2.2.8-GTNH:dev"\n'
        )

        with mock.patch.object(
            checker,
            "fetch_latest_from_metadata",
            return_value=(
                "2.2.9-GTNH",
                "https://example.invalid/maven-metadata.xml",
                ["2.2.8-GTNH", "2.2.9-GTNH", "2.2.10-GTNH-pre"],
            ),
        ):
            state = checker.scan_dependencies(deps_file, timeout_seconds=0.01)

        self.assertEqual(len(state["candidates"]), 1)
        self.assertEqual(state["candidates"][0]["latest_version"], "2.2.9-GTNH")


if __name__ == "__main__":
    unittest.main()
