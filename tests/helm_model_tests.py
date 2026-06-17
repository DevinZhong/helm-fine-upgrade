import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.kube_ops_utils import is_deployment_ready


class KubeOpsUtilsTests(unittest.TestCase):

    @patch('utils.kube_ops_utils.run_cmd')
    def test_is_deployment_ready_true_when_replicas_are_available(self, run_cmd):
        run_cmd.return_value = """
spec:
  replicas: 2
status:
  readyReplicas: 2
  updatedReplicas: 2
  availableReplicas: 2
"""

        self.assertTrue(is_deployment_ready('api', 'demo'))
        run_cmd.assert_called_once_with([
            'kubectl', 'get', 'Deployment', 'api', '-o', 'yaml', '-n', 'demo'
        ])

    @patch('utils.kube_ops_utils.run_cmd')
    def test_is_deployment_ready_false_when_not_available(self, run_cmd):
        run_cmd.return_value = """
spec:
  replicas: 2
status:
  readyReplicas: 1
  updatedReplicas: 2
  availableReplicas: 1
"""

        self.assertFalse(is_deployment_ready('api'))


if __name__ == '__main__':
    unittest.main()
