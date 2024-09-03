#!/usr/bin/env python
#-*- coding:utf-8 -*-

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
