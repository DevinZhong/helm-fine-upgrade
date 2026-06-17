import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.dict_utils import parse_selector, remove_ignore_fields, set_value
from utils.manifest_utils import find_and_merge_related_rendered_manifests_of_deployments


class HelmServiceSupportTests(unittest.TestCase):

    def test_parse_selector_trims_spaces_and_empty_parts(self):
        self.assertEqual(parse_selector('app = web, tier=frontend,'), {
            'app': 'web',
            'tier': 'frontend',
        })

    def test_remove_ignore_fields_tolerates_lists_and_scalars(self):
        manifest = {
            'metadata': {
                'name': 'demo',
                'uid': 'abc',
                'labels': {'keep': 'yes', 'remove': 'no'},
            },
            'spec': {
                'ports': [
                    {'name': 'http', 'nodePort': 30080},
                    {'name': 'metrics', 'nodePort': 30081},
                ],
                'replicas': 2,
            },
            'status': {'ready': True},
        }
        ignore_config = {
            '_fields': ['status'],
            'metadata': {
                '_fields': ['uid'],
                'labels': {'_fields': ['remove']},
            },
            'spec': {
                '_fields': ['replicas'],
                'ports': {'_fields': ['nodePort']},
            },
        }

        remove_ignore_fields(manifest, ignore_config)

        self.assertEqual(manifest, {
            'metadata': {'name': 'demo', 'labels': {'keep': 'yes'}},
            'spec': {'ports': [{'name': 'http'}, {'name': 'metrics'}]},
        })

    def test_set_value_creates_nested_path(self):
        values = {}

        set_value(values, 'image.tag', '1.2.3')

        self.assertEqual(values, {'image': {'tag': '1.2.3'}})

    def test_find_related_manifests_for_deployment(self):
        deployment = {
            'kind': 'Deployment',
            'metadata': {'name': 'api', 'namespace': 'demo'},
            'spec': {
                'template': {
                    'metadata': {'labels': {'app': 'api'}},
                    'spec': {
                        'volumes': [
                            {'configMap': {'name': 'api-config'}},
                            {'secret': {'secretName': 'api-secret'}},
                            {'persistentVolumeClaim': {'claimName': 'api-data'}},
                        ]
                    },
                }
            },
        }
        manifest_dict = {
            'Namespace::demo': {'kind': 'Namespace', 'metadata': {'name': 'demo'}},
            'PersistentVolumeClaim:demo:api-data': {
                'kind': 'PersistentVolumeClaim',
                'metadata': {'name': 'api-data', 'namespace': 'demo'},
                'spec': {'storageClassName': 'fast'},
            },
            'StorageClass::fast': {'kind': 'StorageClass', 'metadata': {'name': 'fast'}},
            'Secret:demo:api-secret': {'kind': 'Secret', 'metadata': {'name': 'api-secret', 'namespace': 'demo'}},
            'ConfigMap:demo:api-config': {'kind': 'ConfigMap', 'metadata': {'name': 'api-config', 'namespace': 'demo'}},
            'Deployment:demo:api': deployment,
            'Service:demo:api': {
                'kind': 'Service',
                'metadata': {'name': 'api', 'namespace': 'demo'},
                'spec': {'selector': {'app': 'api'}},
            },
        }

        related = find_and_merge_related_rendered_manifests_of_deployments(
            [deployment], manifest_dict, ['Service:demo:api'])

        self.assertEqual([manifest['kind'] for manifest in related], [
            'Namespace', 'StorageClass', 'PersistentVolumeClaim',
            'Secret', 'ConfigMap', 'Deployment', 'Service'
        ])


if __name__ == '__main__':
    unittest.main()
