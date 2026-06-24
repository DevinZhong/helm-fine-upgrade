import io
import os
import sys
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.diagnostics_service import build_doctor_report, doctor


class DiagnosticsServiceTests(unittest.TestCase):

    @patch('services.diagnostics_service._get_helm_version')
    @patch('services.diagnostics_service._get_kubectl_version')
    @patch('services.diagnostics_service._detect_plugin_dir')
    @patch('services.diagnostics_service._read_plugin_version')
    def test_build_doctor_report_collects_plugin_platform_and_dependency_info(
            self, read_plugin_version, detect_plugin_dir,
            get_kubectl_version, get_helm_version):
        detect_plugin_dir.return_value = Path(os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')))
        read_plugin_version.return_value = '1.7.0'
        get_helm_version.return_value = {
            'available': True,
            'path': 'C:/tools/helm.exe',
            'version': 'v4.2.2',
            'error': None,
        }
        get_kubectl_version.return_value = {
            'available': False,
            'path': None,
            'version': None,
            'error': 'kubectl not found in PATH',
        }

        report = build_doctor_report()

        self.assertEqual(report['plugin']['version'], '1.7.0')
        self.assertEqual(report['plugin']['mode'], 'source')
        self.assertTrue(report['installation']['source_exists'])
        self.assertTrue(report['installation']['readme_exists'])
        self.assertEqual(report['dependencies']['helm']['version'], 'v4.2.2')
        self.assertEqual(report['dependencies']['kubectl']['error'], 'kubectl not found in PATH')
        self.assertIn('os', report['platform'])
        self.assertIn('arch', report['platform'])

    @patch('services.diagnostics_service.build_doctor_report')
    def test_doctor_supports_json_output(self, build_doctor_report):
        build_doctor_report.return_value = {
            'plugin': {'version': '1.7.0'},
            'dependencies': {'helm': {'available': True}},
        }
        output = io.StringIO()

        with redirect_stdout(output):
            doctor(output_format='json')

        self.assertIn('"version": "1.7.0"', output.getvalue())


if __name__ == '__main__':
    unittest.main()