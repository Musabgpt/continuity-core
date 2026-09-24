import ast
import unittest
from pathlib import Path


class RootRebindingBoundaryTests(unittest.TestCase):
    def test_production_configure_root_usage_is_confined_to_root_boundary(self):
        project_root = Path(__file__).resolve().parents[1]
        offenders = []
        for path in project_root.rglob("*.py"):
            if path.is_relative_to(project_root / "tests"):
                continue
            if path.name in {"continuity.py", "continuity_root.py"}:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "configure_root":
                    offenders.append(f"{path.relative_to(project_root)}:{node.lineno}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "configure_root":
                    offenders.append(f"{path.relative_to(project_root)}:{node.lineno}")
        self.assertEqual(offenders, [], "direct configure_root calls bypass isolated_root: " + ", ".join(offenders))

    def test_root_boundary_is_the_only_runtime_rebinding_adapter(self):
        project_root = Path(__file__).resolve().parents[1]
        root_source = (project_root / "continuity_root.py").read_text(encoding="utf-8")
        self.assertIn("module.configure_root(Path(root))", root_source)
        self.assertIn("module.configure_root(previous_root)", root_source)


if __name__ == "__main__":
    unittest.main()
