import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.dict_utils import parse_selector, remove_ignore_fields, set_value
from utils.manifest_utils import find_and_merge_related_rendered_manifests_of_deployments
from services.helm_service import (build_state_check, build_upgrade_plan,
                                   detect_immutable_field_changes)


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

    def test_detect_immutable_field_changes_for_deployment_selector(self):
        rendered = {
            'kind': 'Deployment',
            'spec': {'selector': {'matchLabels': {'app': 'new'}}},
        }
        cluster = {
            'kind': 'Deployment',
            'spec': {'selector': {'matchLabels': {'app': 'old'}}},
        }

        self.assertEqual(detect_immutable_field_changes(rendered, cluster), [
            'spec.selector'
        ])

    def test_build_upgrade_plan_classifies_common_resource_states(self):
        rendered_manifests = [
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'same', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'changed', 'namespace': 'demo'},
                'data': {'value': '2'},
            },
            {
                'kind': 'Secret',
                'metadata': {'name': 'adopt-me', 'namespace': 'demo'},
                'data': {'token': 'abc'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'new', 'namespace': 'demo'},
                'data': {'value': '3'},
            },
            {
                'kind': 'Deployment',
                'metadata': {'name': 'api', 'namespace': 'demo'},
                'spec': {
                    'selector': {'matchLabels': {'app': 'api-new'}},
                    'template': {
                        'metadata': {'labels': {'app': 'api-new'}},
                        'spec': {'containers': [{'name': 'api', 'image': 'api:1'}]},
                    },
                },
            },
        ]
        cluster_manifests = [
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'same', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'changed', 'namespace': 'demo'},
                'data': {'value': 'old'},
            },
            {
                'kind': 'Deployment',
                'metadata': {'name': 'api', 'namespace': 'demo'},
                'spec': {
                    'selector': {'matchLabels': {'app': 'api-old'}},
                    'template': {
                        'metadata': {'labels': {'app': 'api-old'}},
                        'spec': {'containers': [{'name': 'api', 'image': 'api:1'}]},
                    },
                },
            },
            {
                'kind': 'Service',
                'metadata': {'name': 'old', 'namespace': 'demo'},
                'spec': {'ports': [{'port': 80}]},
            },
        ]

        def lookup(kind, name, namespace=None):
            if kind == 'Secret' and name == 'adopt-me' and namespace == 'demo':
                return {
                    'kind': 'Secret',
                    'metadata': {'name': 'adopt-me', 'namespace': 'demo'},
                    'data': {'token': 'abc'},
                }
            return None

        plan = build_upgrade_plan(
            rendered_manifests,
            cluster_manifests,
            {'ignore_fields': {}},
            lookup_manifest_func=lookup)

        self.assertEqual(plan['summary'], {
            'create': 1,
            'update': 2,
            'unchanged': 1,
            'adopt': 1,
            'orphan': 1,
            'immutable_risk': 1,
        })
        resource_statuses = {
            resource['key']: resource['status']
            for resource in plan['resources']
        }
        self.assertEqual(resource_statuses['ConfigMap:demo:same'], 'unchanged')
        self.assertEqual(resource_statuses['ConfigMap:demo:changed'], 'update')
        self.assertEqual(resource_statuses['Secret:demo:adopt-me'], 'adopt')
        self.assertEqual(resource_statuses['ConfigMap:demo:new'], 'create')
        self.assertEqual(resource_statuses['Service:demo:old'], 'orphan')
        deployment_plan = [
            resource for resource in plan['resources']
            if resource['key'] == 'Deployment:demo:api'
        ][0]
        self.assertEqual(deployment_plan['immutable_field_changes'], [
            'spec.selector'
        ])

    def test_build_state_check_reports_runtime_and_chart_drift(self):
        release_manifests = [
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'same', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'runtime-drift', 'namespace': 'demo'},
                'data': {'value': 'release'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'missing-runtime', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'delete-from-chart', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
        ]
        runtime_manifests = [
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'same', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'runtime-drift', 'namespace': 'demo'},
                'data': {'value': 'runtime'},
            },
            {
                'kind': 'Secret',
                'metadata': {'name': 'runtime-extra', 'namespace': 'demo'},
                'data': {'token': 'abc'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'delete-from-chart', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
        ]
        chart_manifests = [
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'same', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'runtime-drift', 'namespace': 'demo'},
                'data': {'value': 'chart'},
            },
            {
                'kind': 'ConfigMap',
                'metadata': {'name': 'missing-runtime', 'namespace': 'demo'},
                'data': {'value': '1'},
            },
            {
                'kind': 'Secret',
                'metadata': {'name': 'chart-create', 'namespace': 'demo'},
                'data': {'token': 'abc'},
            },
        ]

        result = build_state_check(
            release_manifests, runtime_manifests, chart_manifests,
            {'ignore_fields': {}})

        self.assertEqual(result['summary'], {
            'release_resources': 4,
            'runtime_resources': 4,
            'chart_resources': 4,
            'runtime_missing': 1,
            'runtime_extra': 1,
            'runtime_drift': 1,
            'chart_create': 1,
            'chart_update': 1,
            'chart_delete': 1,
        })
        self.assertEqual(
            result['runtime_consistency']['missing_from_runtime'][0]['key'],
            'ConfigMap:demo:missing-runtime')
        self.assertEqual(
            result['runtime_consistency']['extra_in_runtime'][0]['key'],
            'Secret:demo:runtime-extra')
        self.assertEqual(
            result['chart_consistency']['extra_in_chart'][0]['key'],
            'Secret:demo:chart-create')
        self.assertEqual(
            result['chart_consistency']['missing_from_chart'][0]['key'],
            'ConfigMap:demo:delete-from-chart')


if __name__ == '__main__':
    unittest.main()
