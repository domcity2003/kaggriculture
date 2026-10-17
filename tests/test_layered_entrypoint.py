"""The wrapper must run, not merely reproduce the parent's no-op result."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class LayerEntrypointTests(unittest.TestCase):
    def build(self, base, layer):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "base.py").write_text(base)
            (root / "layer.py").write_text(layer)
            subprocess.run([sys.executable, str(ROOT / "tools/build_layered.py"),
                            "--base", str(root / "base.py"),
                            "--layer", str(root / "layer.py"),
                            "--out", str(root / "main.py")],
                           check=True, capture_output=True)
            source = (root / "main.py").read_text()
        namespace = {}
        exec(compile(source, "main.py", "exec"), namespace)
        # Exact callable selection used by Kaggle's agent loader.
        entry = [value for value in namespace.values() if callable(value)][-1]
        return entry, namespace

    def test_nontrivial_wrapper_is_selected_after_parent_alias(self):
        entry, namespace = self.build(
            'def agent(obs, cfg=None):\n    return {"parent": True}\n',
            '_PARENT = agent\ndef agent(obs, cfg=None):\n'
            '    action = _PARENT(obs, cfg)\n    action["layer"] = True\n    return action\n')
        self.assertIs(entry, namespace["agent"])
        self.assertEqual(entry({}), {"parent": True, "layer": True})

    def test_preserves_real_base_entry_even_when_not_named_agent(self):
        entry, _ = self.build(
            'def agent(obs, cfg=None):\n    return {"stale": True}\n'
            'def actual_submission(obs, cfg=None):\n    return {"real": True}\n',
            '_PARENT = agent\ndef agent(obs, cfg=None):\n'
            '    action = _PARENT(obs, cfg)\n    action["layer"] = True\n    return action\n'
            'def later_helper():\n    return "must not be selected"\n')
        self.assertEqual(entry({}), {"real": True, "layer": True})


if __name__ == "__main__":
    unittest.main()
