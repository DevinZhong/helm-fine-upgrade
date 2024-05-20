#!/usr/bin/env python
#-*- coding:utf-8 -*-

import yaml
from utils.shell_utils import run_shell_cmd

K8S_KINDS = ['PodDisruptionBudget', 'ServiceAccount', 'Secret', 'ConfigMap',
             'PersistentVolume', 'PersistentVolumeClaim', 'Role', 'RoleBinding',
             'Service', 'Deployment', 'HorizontalPodAutoscaler', 'CronJob', 'Endpoints']

def get_api_object_spec(kind, name, namespace, kubeconfig, debug):
    """
    根据元信息，使用 kubectl 获取API对象的 yaml 配置
    """
    cmd = f'kubectl get {kind} {name} -o yaml'
    if namespace is not None:
        cmd += f' -n {namespace}'
    if kubeconfig is not None:
        cmd += f' --kubeconfig={kubeconfig}'
    cmd_output = run_shell_cmd(cmd, debug)
    if cmd_output is not None:
        return yaml.safe_load(cmd_output)
    else:
        return None
    
def get_all_release_api_objects(release_name, release_namespace, kubeconfig, debug) -> list:
    """获取集群中所有由 Helm Release 管理的 API 对象

    Args:
        release_name (string): release name
        release_namespace (string): release namespace
        kubeconfig (string): kubeconfig path
        debug (boolean): debug mode flag

    Returns:
        list: API 对象配置列表
    """
    kinds = ','.join(K8S_KINDS)
    cmd = f'kubectl get {kinds} --all-namespaces -l app.kubernetes.io/managed-by=Helm -o yaml'
    if kubeconfig is not None:
        cmd += f' --kubeconfig {kubeconfig}'
    cmd_output = run_shell_cmd(cmd, debug)
    if cmd_output is not None:
        release_runtime_manifests = []
        manifests = yaml.safe_load(cmd_output)['items']
        for manifest in manifests:
            if 'annotations' not in manifest['metadata']:
                continue
            annotations = manifest['metadata']['annotations']
            if 'meta.helm.sh/release-name' not in annotations or 'meta.helm.sh/release-namespace' not in annotations:
                continue
            manifest_release_name = annotations['meta.helm.sh/release-name']
            manifest_release_namespace = annotations['meta.helm.sh/release-namespace']
            if manifest_release_name != release_name or manifest_release_namespace != release_namespace:
                continue
            else:
                release_runtime_manifests.append(manifest)
        return release_runtime_manifests                                    
    else:
        return None

def get_manifest_unique_key(manifest: dict) -> str:
    """从 Manifest 中提取唯一 key

    Args:
        manifest (dict): Manifest 字段信息

    Returns:
        str: 唯一 key
    """
    kind = manifest['kind']
    name = manifest['metadata']['name']
    if 'namespace' in manifest['metadata']:
        namespace = manifest['metadata']['namespace']
    else:
        namespace = ''
    return f'{kind}:{namespace}:{name}'

def manifests_list_to_dict(manifests: list) -> dict:
    """根据唯一 key，将 Manifest 数组转换为字典

    Args:
        manifests (list): Manifest list

    Returns:
        dict: 转化后的字典
    """
    return {get_manifest_unique_key(d): d for d in manifests}