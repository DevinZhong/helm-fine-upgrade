#!/usr/bin/env python
#-*- coding:utf-8 -*-

import itertools
from typing import List

def parse_config_maps_in_deployment(manifest: dict) -> List[str]:
    """解析 Deployment manifest 中关联的 ConfigMap

    Args:
        manifest (dict): 传入 Deployment manifest

    Returns:
        List[str]: 关联的 ConfigMap 名称
    """
    if 'spec' not in manifest:
        return []
    if 'template' not in manifest['spec']:
        return []
    if 'spec' not in manifest['spec']['template']:
        return []
    if 'volumes' not in manifest['spec']['template']['spec']:
        return []
    return [volume['configMap']['name'] for volume in manifest['spec']['template']['spec']['volumes'] if 'configMap' in volume]

def parse_secrets_in_deployment(manifest: dict) -> List[str]:
    """解析 Deployment manifest 中关联的 Secret

    Args:
        manifest (dict): 传入 Deployment manifest

    Returns:
        List[str]: 关联的 Secret 名称
    """
    if 'spec' not in manifest:
        return []
    if 'template' not in manifest['spec']:
        return []
    if 'spec' not in manifest['spec']['template']:
        return []
    if 'volumes' not in manifest['spec']['template']['spec']:
        return []
    return [volume['secret']['secretName'] for volume in manifest['spec']['template']['spec']['volumes'] if 'secret' in volume]

def parse_pvcs_in_deployment(manifest: dict) -> List[str]:
    """解析 Deployment manifest 中关联的 pvc

    Args:
        manifest (dict): 传入 Deployment manifest

    Returns:
        List[str]: 关联的 pvc 名称
    """
    if 'spec' not in manifest:
        return []
    if 'template' not in manifest['spec']:
        return []
    if 'spec' not in manifest['spec']['template']:
        return []
    if 'volumes' not in manifest['spec']['template']['spec']:
        return []
    return [volume['persistentVolumeClaim']['claimName'] for volume in manifest['spec']['template']['spec']['volumes'] if 'persistentVolumeClaim' in volume]

def parse_pvcs_in_deployment(manifest: dict) -> List[str]:
    """解析 Deployment manifest 中关联的 pvc

    Args:
        manifest (dict): 传入 Deployment manifest

    Returns:
        List[str]: 关联的 pvc 名称
    """
    if 'spec' not in manifest:
        return []
    if 'template' not in manifest['spec']:
        return []
    if 'spec' not in manifest['spec']['template']:
        return []
    if 'volumes' not in manifest['spec']['template']['spec']:
        return []
    return [volume['persistentVolumeClaim']['claimName'] for volume in manifest['spec']['template']['spec']['volumes'] if 'persistentVolumeClaim' in volume]

def parse_storageclass_in_pvc(manifest: dict) -> str:
    """解析 pvc manifest 中关联的 storageclass

    Args:
        manifest (dict): 传入 pvc manifest

    Returns:
        List[str]: 关联的 storageclass 名称
    """
    if 'spec' not in manifest:
        return None
    if 'storageClassName' not in manifest['spec']:
        return None
    return manifest['spec']['storageClassName']

def parse_pv_in_pvc(manifest: dict) -> str:
    """解析 pvc manifest 中关联的 pv

    Args:
        manifest (dict): 传入 pvc manifest

    Returns:
        List[str]: 关联的 pv 名称
    """
    if 'spec' not in manifest:
        return None
    if 'volumeName' not in manifest['spec']:
        return None
    return manifest['spec']['volumeName']

def find_and_merge_related_rendered_manifests_of_deployments(deployment_manifests: List[dict],
                                                             manifest_dict: dict,
                                                             service_unique_keys: List[str]) -> List[dict]:
    """找出与 Deployment 关联的其他 manifest 资源

    Args:
        deployment_manifests (List[dict]): Deployment manifest 数组
        manifest_dict (dict): 所有 manifest 的字典，key 为 kind:bamespace:name 格式
        service_unique_keys (List[str]): svc 在字典中的唯一 key 数组

    Returns:
        List[dict]: 合并后的 manifest 新数组
    """

    related_namespace_manifests = []
    related_configmap_manifests = []
    related_secrets_manifests = []
    related_pvc_manifests = []
    related_service_manifests = []
    related_storageclass_manifests = []
    unique_key_set = set()

    for rendered_manifest in deployment_manifests:
        if 'namespace' in rendered_manifest['metadata']:
            namespace = rendered_manifest['metadata']['namespace']
        else:
            namespace = ''

        # 提取 Deployment 关联的 Namespace
        namespace_unique_key = f'Namespace::{namespace}'
        if namespace_unique_key in manifest_dict and namespace_unique_key not in unique_key_set:
            related_namespace_manifests.append(manifest_dict[namespace_unique_key])
            unique_key_set.add(namespace_unique_key)

        # 提取 Deployment 关联的 PVC
        for pvc_name in parse_pvcs_in_deployment(rendered_manifest):
            pvc_unique_key = f'PersistentVolumeClaim:{namespace}:{pvc_name}'
            if pvc_unique_key in manifest_dict and pvc_unique_key not in unique_key_set:
                pvc = manifest_dict[pvc_unique_key]
                related_pvc_manifests.append(pvc)
                unique_key_set.add(pvc_unique_key)
                # 提取 PVC 关联的 StorageClass
                storageclass_name = parse_storageclass_in_pvc(pvc)
                if storageclass_name is not None:
                    sc_unique_key = f'StorageClass::{storageclass_name}'
                    if sc_unique_key in manifest_dict and sc_unique_key not in unique_key_set:
                        related_storageclass_manifests.append(manifest_dict[sc_unique_key])
                        unique_key_set.add(sc_unique_key)
                else:
                    pv_name = parse_pv_in_pvc(pvc)
                    if pv_name is not None:
                        pv_unique_key = f'PersistentVolume::{pv_name}'
                        if pv_unique_key in manifest_dict and pv_unique_key not in unique_key_set:
                            related_storageclass_manifests.append(manifest_dict[pv_unique_key])
                            unique_key_set.add(pv_unique_key)

        # 提取 Deployment 关联的 Secret
        for secret_name in parse_secrets_in_deployment(rendered_manifest):
            secret_unique_key = f'Secret:{namespace}:{secret_name}'
            if secret_unique_key in manifest_dict and secret_unique_key not in unique_key_set:
                related_secrets_manifests.append(manifest_dict[secret_unique_key])
                unique_key_set.add(secret_unique_key)
        # 提取 Deployment 关联的 ConfigMap
        for configmap_name in parse_config_maps_in_deployment(rendered_manifest):
            configmap_unique_key = f'ConfigMap:{namespace}:{configmap_name}'
            if configmap_unique_key in manifest_dict and configmap_unique_key not in unique_key_set:
                related_configmap_manifests.append(manifest_dict[configmap_unique_key])
                unique_key_set.add(configmap_unique_key)

        # 提取 Deployment 关联的 Service
        pod_labels = rendered_manifest['spec']['template']['metadata']['labels']
        for svc_key in service_unique_keys:
            svc = manifest_dict[svc_key]
            if 'selector' not in svc['spec']:
                continue
            svc_selector = svc['spec']['selector']
            if svc_key not in unique_key_set and all(item in pod_labels.items() for item in svc_selector.items()):
                related_service_manifests.append(svc)
                unique_key_set.add(svc_key)

    return list(itertools.chain(related_namespace_manifests,
                                related_storageclass_manifests,
                                related_pvc_manifests,
                                related_secrets_manifests,
                                related_configmap_manifests,
                                deployment_manifests,
                                related_service_manifests))
