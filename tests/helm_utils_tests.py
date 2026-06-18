import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from utils.helm_utils import (build_helm_get_manifest_cmd,
                              build_kubectl_cmd,
                              build_helm_template_cmd,
                              configure_kube_options,
                              find_first_same_object_key_with_different_hash,
                              get_container_image_versions,
                              get_helm_namespace,
                              get_manifest_namespace,
                              get_manifest_unique_key,
                              get_image_version,
                              manifests_list_to_dict)


class HelmUtilsTests(unittest.TestCase):

    def setUp(self):
        self.original_env = {
            key: os.environ.get(key)
            for key in (
                'HELM_NAMESPACE',
                'FINE_UPGRADE_KUBECONFIG',
                'FINE_UPGRADE_KUBE_CONTEXT',
                'FINE_UPGRADE_TIMEOUT',
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

    def test_build_helm_template_cmd_uses_argument_list(self):
        cmd = build_helm_template_cmd('my release', './chart dir', './values file.yaml')

        self.assertEqual(cmd, [
            'helm', 'template', '--is-upgrade', '--no-hooks', '--skip-crds',
            'my release', './chart dir', '-f', './values file.yaml',
            '--namespace', 'default'
        ])

    def test_build_helm_get_manifest_cmd_uses_release_namespace(self):
        os.environ['HELM_NAMESPACE'] = 'demo'
        self.assertEqual(build_helm_get_manifest_cmd('my release'), [
            'helm', 'get', 'manifest', 'my release', '--namespace', 'demo'
        ])

    def test_configure_kube_options_appends_helm_and_kubectl_globals(self):
        configure_kube_options(namespace='demo',
                               kubeconfig='./kube config.yaml',
                               context='dev',
                               timeout='30s')

        self.assertEqual(build_helm_get_manifest_cmd('release'), [
            'helm', 'get', 'manifest', 'release',
            '--namespace', 'demo',
            '--kubeconfig', './kube config.yaml',
            '--kube-context', 'dev',
        ])
        self.assertEqual(build_kubectl_cmd(['get', 'pod', 'api']), [
            'kubectl', 'get', 'pod', 'api',
            '--kubeconfig', './kube config.yaml',
            '--context', 'dev',
            '--request-timeout', '30s',
        ])

    def test_get_helm_namespace_defaults_to_default(self):
        self.assertEqual(get_helm_namespace(), 'default')

    def test_manifests_list_to_dict_ignores_none_documents(self):
        manifests = [
            None,
            {'kind': 'ConfigMap', 'metadata': {'name': 'app', 'namespace': 'demo'}},
        ]

        result = manifests_list_to_dict(manifests)

        self.assertEqual(list(result.keys()), ['ConfigMap:demo:app'])

    def test_manifest_unique_key_defaults_namespaced_resources_to_helm_namespace(self):
        os.environ['HELM_NAMESPACE'] = 'demo'
        self.assertEqual(
            get_manifest_unique_key({
                'kind': 'ConfigMap',
                'metadata': {'name': 'app'},
            }),
            'ConfigMap:demo:app')
        self.assertEqual(
            get_manifest_namespace({
                'kind': 'ConfigMap',
                'metadata': {'name': 'app'},
            }),
            'demo')
        self.assertEqual(
            get_manifest_unique_key({
                'kind': 'Namespace',
                'metadata': {'name': 'demo'},
            }),
            'Namespace::demo')

    def test_find_first_same_object_key_with_different_hash(self):
        keys = {
            'ConfigMap:demo:app-cafebabe',
            'ConfigMap:demo:other-12345678',
        }

        result = find_first_same_object_key_with_different_hash(
            keys, 'ConfigMap:demo:app-deadbeef')

        self.assertEqual(result, 'ConfigMap:demo:app-cafebabe')

    def test_get_container_image_versions_supports_multiple_containers(self):
        manifest = {
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {'name': 'api', 'image': 'registry.local/team/api:1.2.3'},
                            {'name': 'sidecar', 'image': 'registry.local/team/sidecar@sha256:abc123'},
                        ]
                    }
                }
            }
        }

        self.assertEqual(get_container_image_versions(manifest), {
            'api': '1.2.3',
            'sidecar': 'abc123',
        })
        self.assertEqual(get_image_version(manifest), '1.2.3')


if __name__ == '__main__':
    unittest.main()
