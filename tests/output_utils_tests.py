import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.output_utils import (
    FAILURE_EXIT_CODE,
    exit_if_fail_on_triggered,
    get_triggered_failures,
    parse_fail_on,
    print_structured_output,
)


class OutputUtilsTests(unittest.TestCase):

    def test_print_structured_output_supports_json(self):
        output = io.StringIO()

        with redirect_stdout(output):
            print_structured_output({'message': 'hello', 'count': 2}, 'json')

        self.assertEqual(json.loads(output.getvalue()), {
            'message': 'hello',
            'count': 2,
        })

    def test_print_structured_output_supports_yaml(self):
        output = io.StringIO()

        with redirect_stdout(output):
            print_structured_output({'message': 'hello'}, 'yaml')

        self.assertIn('message: hello', output.getvalue())

    def test_parse_fail_on_splits_comma_separated_fields(self):
        self.assertEqual(parse_fail_on(' update, immutable_risk,,adopt '), {
            'update',
            'immutable_risk',
            'adopt',
        })

    def test_get_triggered_failures_uses_summary_counts(self):
        result = {
            'summary': {
                'update': 2,
                'adopt': 0,
                'immutable_risk': 1,
            }
        }

        self.assertEqual(
            get_triggered_failures(result, 'update,adopt,immutable_risk'),
            {
                'immutable_risk': 1,
                'update': 2,
            })

    def test_exit_if_fail_on_triggered_uses_ci_exit_code(self):
        with self.assertRaises(SystemExit) as context:
            exit_if_fail_on_triggered(
                {'summary': {'runtime_drift': 1}},
                'runtime_drift')

        self.assertEqual(context.exception.code, FAILURE_EXIT_CODE)


if __name__ == '__main__':
    unittest.main()
