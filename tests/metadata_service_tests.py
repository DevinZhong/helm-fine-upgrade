import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.metadata_service import (build_adopt_plan,
                                       build_set_ownership_commands,
                                       get_ownership_metadata)


class MetadataServiceTests(unittest.TestCase):

    def setUp(self):
        self.original_namespace = os.environ.get('HELM_NAMESPACE')
        os.environ['HELM_NAMESPACE'] = 'demo'

    def tearDown(self):
        if self.original_namespace is None:
            os.environ.pop('HELM_NAMESPACE', None)
        else:
            os.environ['HELM_NAMESPACE'] = self.original_namespace

    def test_get_ownership_metadata_reads_helm_fields(self):
        manifest = {
            'metadata': {
                'annotations': {
                    'meta.helm.sh/release-name': 'app',
                    'meta.helm.sh/release-namespace': 'demo',
                },
                'labels': {'app.kubernetes.io/managed-by': 'Helm'},
            }
        }

        self.assertEqual(get_ownership_metadata(manifest), {
            'release_name': 'app',
            'release_namespace': 'demo',
            'managed_by': 'Helm',
        })

    def test_build_set_ownership_commands_includes_namespace_for_namespaced_resource(self):
        commands = build_set_ownership_commands(
            'ConfigMap', 'app', 'demo', 'release', 'demo')

        self.assertEqual(commands, [
            ['kubectl', 'annotate', 'ConfigMap', 'app',
             'meta.helm.sh/release-name=release', '--overwrite', '-n', 'demo'],
            ['kubectl', 'annotate', 'ConfigMap', 'app',
             'meta.helm.sh/release-namespace=demo', '--overwrite', '-n', 'demo'],
            ['kubectl', 'label', 'ConfigMap', 'app',
             'app.kubernetes.io/managed-by=Helm', '--overwrite', '-n', 'demo'],
        ])

    def test_build_adopt_plan_classifies_ownership_states(self):
        rendered_manifests = [
            {'kind': 'ConfigMap', 'metadata': {'name': 'managed'}},
            {'kind': 'ConfigMap', 'metadata': {'name': 'adoptable'}},
            {'kind': 'ConfigMap', 'metadata': {'name': 'needs-update'}},
            {'kind': 'ConfigMap', 'metadata': {'name': 'conflict'}},
            {'kind': 'ConfigMap', 'metadata': {'name': 'missing'}},
        ]

        def lookup(kind, name, namespace=None):
            manifests = {
                'managed': {
                    'kind': kind,
                    'metadata': {
                        'name': name,
                        'namespace': namespace,
                        'annotations': {
                            'meta.helm.sh/release-name': 'release',
                            'meta.helm.sh/release-namespace': 'demo',
                        },
                        'labels': {'app.kubernetes.io/managed-by': 'Helm'},
                    },
                },
                'adoptable': {
                    'kind': kind,
                    'metadata': {'name': name, 'namespace': namespace},
                },
                'needs-update': {
                    'kind': kind,
                    'metadata': {
                        'name': name,
                        'namespace': namespace,
                        'annotations': {
                            'meta.helm.sh/release-name': 'release',
                        },
                    },
                },
                'conflict': {
                    'kind': kind,
                    'metadata': {
                        'name': name,
                        'namespace': namespace,
                        'annotations': {
                            'meta.helm.sh/release-name': 'other',
                            'meta.helm.sh/release-namespace': 'demo',
                        },
                        'labels': {'app.kubernetes.io/managed-by': 'Helm'},
                    },
                },
            }
            return manifests.get(name)

        plan = build_adopt_plan(
            rendered_manifests, 'release', lookup_manifest_func=lookup)

        self.assertEqual(plan['summary'], {
            'managed': 1,
            'adoptable': 1,
            'needs_metadata_update': 1,
            'conflict': 1,
            'missing': 1,
        })
        statuses = {
            resource['name']: resource['status']
            for resource in plan['resources']
        }
        self.assertEqual(statuses, {
            'managed': 'managed',
            'adoptable': 'adoptable',
            'needs-update': 'needs_metadata_update',
            'conflict': 'conflict',
            'missing': 'missing',
        })
        adoptable = [
            resource for resource in plan['resources']
            if resource['name'] == 'adoptable'
        ][0]
        self.assertEqual(adoptable['commands'][0],
                         'kubectl annotate ConfigMap adoptable '
                         'meta.helm.sh/release-name=release --overwrite -n demo')
        conflict = [
            resource for resource in plan['resources']
            if resource['name'] == 'conflict'
        ][0]
        self.assertNotIn('commands', conflict)


if __name__ == '__main__':
    unittest.main()
