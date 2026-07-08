import io
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from main import (
    CONFIRMATION_REQUIRED_EXIT_CODE,
    build_parser,
    configure_runtime_options,
    validate_safety_options,
)


class MainCliTests(unittest.TestCase):

    def setUp(self):
        self.original_env = {
            key: os.environ.get(key)
            for key in (
                'HELM_NAMESPACE',
                'FINE_UPGRADE_KUBECONFIG',
                'FINE_UPGRADE_KUBE_CONTEXT',
                'FINE_UPGRADE_TIMEOUT',
                'DRY_RUN_FLAG',
                'HELM_DEBUG',
            )
        }
        for key in self.original_env:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_plan_subcommand_parses_kubernetes_connection_flags(self):
        args = build_parser().parse_args([
            'plan', 'release', './chart',
            '--namespace', 'demo',
            '--kubeconfig', './kubeconfig.yaml',
            '--kube-context', 'dev',
            '--timeout', '30s',
            '--output-format', 'json',
            '--fail-on', 'immutable_risk,adopt',
            '--dry-run',
            '--debug',
        ])

        self.assertEqual(args.action, 'plan')
        self.assertEqual(args.release_name, 'release')
        self.assertEqual(args.chart, './chart')
        self.assertEqual(args.namespace, 'demo')
        self.assertEqual(args.kubeconfig, './kubeconfig.yaml')
        self.assertEqual(args.context, 'dev')
        self.assertEqual(args.timeout, '30s')
        self.assertEqual(args.output_format, 'json')
        self.assertEqual(args.fail_on, 'immutable_risk,adopt')
        self.assertTrue(args.dry_run)
        self.assertTrue(args.debug)

    def test_doctor_subcommand_supports_structured_output(self):
        args = build_parser().parse_args([
            'doctor',
            '--output-format', 'json',
            '--debug',
        ])

        self.assertEqual(args.action, 'doctor')
        self.assertEqual(args.output_format, 'json')
        self.assertTrue(args.debug)

    def test_configure_runtime_options_sets_environment(self):
        args = build_parser().parse_args([
            'apply', 'release', './chart',
            '--namespace', 'demo',
            '--kubeconfig', './kubeconfig.yaml',
            '--context', 'dev',
            '--timeout', '30s',
            '--dry-run',
            '--debug',
        ])

        configure_runtime_options(args)

        self.assertEqual(os.environ['HELM_NAMESPACE'], 'demo')
        self.assertEqual(os.environ['FINE_UPGRADE_KUBECONFIG'], './kubeconfig.yaml')
        self.assertEqual(os.environ['FINE_UPGRADE_KUBE_CONTEXT'], 'dev')
        self.assertEqual(os.environ['FINE_UPGRADE_TIMEOUT'], '30s')
        self.assertEqual(os.environ['DRY_RUN_FLAG'], '1')
        self.assertEqual(os.environ['HELM_DEBUG'], '1')

    def test_mutating_command_requires_yes_without_dry_run_in_noninteractive_mode(self):
        args = build_parser().parse_args([
            'apply', 'release', './chart',
        ])
        input_stream = io.StringIO('')
        output_stream = io.StringIO()

        with self.assertRaises(SystemExit) as context:
            validate_safety_options(args, input_stream=input_stream, output_stream=output_stream)

        self.assertEqual(context.exception.code, CONFIRMATION_REQUIRED_EXIT_CODE)
        self.assertIn('pass --yes', output_stream.getvalue())

    def test_mutating_command_cancels_without_error_when_interactive_answer_is_no(self):
        args = build_parser().parse_args([
            'apply', 'release', './chart',
        ])
        input_stream = io.StringIO('\n')
        input_stream.isatty = lambda: True
        output_stream = io.StringIO()

        with self.assertRaises(SystemExit) as context:
            validate_safety_options(args, input_stream=input_stream, output_stream=output_stream)

        self.assertEqual(context.exception.code, 0)
        self.assertIn('Proceed? [y/N]', output_stream.getvalue())
        self.assertIn('Cancelled. No changes were made.', output_stream.getvalue())

    def test_mutating_command_allows_interactive_yes(self):
        args = build_parser().parse_args([
            'apply', 'release', './chart',
        ])
        input_stream = io.StringIO('y\n')
        input_stream.isatty = lambda: True
        output_stream = io.StringIO()

        validate_safety_options(args, input_stream=input_stream, output_stream=output_stream)

        self.assertIn('Proceed? [y/N]', output_stream.getvalue())

    def test_mutating_command_allows_dry_run_without_yes(self):
        args = build_parser().parse_args([
            'update-ownership-metadata', 'release', './chart',
            '--dry-run',
        ])

        validate_safety_options(args)

    def test_mutating_command_allows_explicit_yes(self):
        args = build_parser().parse_args([
            'rolling-update-pod-labels', 'release', './chart',
            '--yes',
        ])

        validate_safety_options(args)

    def test_read_only_command_does_not_require_yes(self):
        args = build_parser().parse_args([
            'plan', 'release', './chart',
        ])

        validate_safety_options(args)


if __name__ == '__main__':
    unittest.main()
