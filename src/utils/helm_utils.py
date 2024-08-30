#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
from typing import Iterable
import yaml
from utils.shell_utils import run_shell_cmd
from utils.dict_utils import parse_selector

HELM_NAMESPACE = os.environ.get('HELM_NAMESPACE')

K8S_KINDS = ['PodDisruptionBudget', 'ServiceAccount', 'Secret', 'ConfigMap',
             'PersistentVolume', 'PersistentVolumeClaim', 'Role', 'RoleBinding',
             'Service', 'Deployment', 'HorizontalPodAutoscaler', 'CronJob', 'Endpoints']

def get_api_object_spec(kind, name, namespace):
    """
    根据元信息，使用 kubectl 获取API对象的 yaml 配置
    """
    cmd = f'kubectl get {kind} {name} -o yaml'
    if namespace is not None:
        cmd += f' -n {namespace}'
    cmd_output = run_shell_cmd(cmd)
    if cmd_output is not None:
        return yaml.safe_load(cmd_output)
    else:
        return None
    
def get_all_release_api_objects(release_name) -> list:
    """获取集群中所有由 Helm Release 管理的 API 对象

    Args:
        release_name (string): release name

    Returns:
        list: API 对象配置列表
    """
    kinds = ','.join(K8S_KINDS)
    cmd = f'kubectl get {kinds} --all-namespaces -l app.kubernetes.io/managed-by=Helm -o yaml'
    cmd_output = run_shell_cmd(cmd)
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
            if manifest_release_name != release_name or manifest_release_namespace != HELM_NAMESPACE:
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

def get_image_version(manifest: dict) -> str:
    """从 manifest 中提取镜像版本号

    Args:
        manifest (dict): manifest dict

    Returns:
        str: docker image tag
    """
    image = manifest['spec']['template']['spec']['containers'][0]['image']
    parts = image.split(':')
    return parts[1]

def find_first_same_object_key_with_different_hash(keys: Iterable, object_key: str) -> str:
    """从 keys 中寻找只是末尾 hash 不同的对象唯一 key，常用语 Helm 中 ConfigMap 的匹配

    Args:
        keys (Iterable): 可用于遍历的 keys，可以是 list 或 set
        object_key (str): 寻找匹配的 key

    Returns:
        str: 匹配到的第一个 key
    """
    # print(f'keys: {keys}, object_key: {object_key}')
    for key in keys:
        # key 长度不同，排除
        if len(key) != len(object_key):
            continue
        # 分隔最后一个 ·-· 符号，符号前为对象基础名称，符号后为 hash
        key_parts = key.rsplit("-", 1)
        object_key_parts = object_key.rsplit("-", 1)
        # 没有 `-`` 符号，排除
        if len(key_parts) != 2 or len(object_key_parts) != 2:
            continue 
        # 对象名部分必须相等，否则跳过
        if key_parts[0] != object_key_parts[0]:
            continue
        # print(f"any: {any(c not in '0123456789abcdef' for c in key.lower())}")
        # hash 部分只能包含16进制数值，否则跳过
        if any(c not in '0123456789abcdef' for c in key_parts[1].lower()) or any(c not in '0123456789abcdef' for c in object_key_parts[1].lower()):
            continue
        # 找到满足的 key
        return key
    return None

def is_manifest_match_selector(manifest: dict, selector: str) -> bool:
    if not selector:
        return True
    try:
        selector_dict = parse_selector(selector)
    except Exception as e:
        print(e)
        return False

    if 'metadata' not in manifest:
        return False
    if 'labels' not in manifest['metadata']:
        return False
    labels=manifest['metadata']['labels']

    for key, value in selector_dict.items():
        if key not in labels or labels[key] != value:
            return False
    return True
