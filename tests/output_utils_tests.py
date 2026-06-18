import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.output_utils import print_structured_output


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


if __name__ == '__main__':
    unittest.main()
