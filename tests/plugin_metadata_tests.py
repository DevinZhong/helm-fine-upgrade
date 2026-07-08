import unittest
from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]


class PluginMetadataTests(unittest.TestCase):
    def test_source_plugin_uses_binary_install_hooks_and_wrappers(self):
        plugin = yaml.safe_load((ROOT_DIR / "plugin.yaml").read_text())

        self.assertEqual("1.7.1", plugin["version"])
        self.assertNotIn("command", plugin)

        commands = plugin["platformCommand"]
        self.assertEqual("powershell.exe", commands[0]["command"])
        self.assertIn("scripts\\run.ps1", commands[0]["args"][-1])
        self.assertEqual("sh", commands[1]["command"])
        self.assertEqual(["${HELM_PLUGIN_DIR}/scripts/run.sh"], commands[1]["args"])

        hooks = plugin["platformHooks"]
        self.assertIn("install", hooks)
        self.assertIn("update", hooks)
        self.assertEqual("powershell.exe", hooks["install"][0]["command"])
        self.assertIn("scripts\\install.ps1", hooks["install"][0]["args"][-1])
        self.assertEqual("sh", hooks["install"][1]["command"])
        self.assertEqual(["${HELM_PLUGIN_DIR}/scripts/install.sh"], hooks["install"][1]["args"])
        self.assertEqual("powershell.exe", hooks["update"][0]["command"])
        self.assertEqual("-Update", hooks["update"][0]["args"][-1])
        self.assertEqual("sh", hooks["update"][1]["command"])
        self.assertEqual(["${HELM_PLUGIN_DIR}/scripts/install.sh", "--update"], hooks["update"][1]["args"])

    def test_install_and_runtime_scripts_exist(self):
        for script in [
            "scripts/install.sh",
            "scripts/run.sh",
            "scripts/install.ps1",
            "scripts/run.ps1",
        ]:
            self.assertTrue((ROOT_DIR / script).is_file(), script)


if __name__ == "__main__":
    unittest.main()

