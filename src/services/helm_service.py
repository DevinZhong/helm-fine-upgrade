#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
import yaml
import itertools
from typing import List
from utils.yaml_utils import init_yaml_representer
from utils.shell_utils import run_shell_cmd
from utils.dict_utils import remove_ignore_fields, parse_selector
from utils.helm_utils import (
    get_api_object_spec,
    get_all_release_api_objects,
    manifests_list_to_dict,
    get_manifest_unique_key,
    find_first_same_object_key_with_different_hash,
    is_manifest_match_selector
    )   
from utils.manifest_utils import (
    parse_config_maps_in_deployment,
    parse_secrets_in_deployment,
    parse_pvcs_in_deployment,
    parse_storageclass_in_pvc    
    )

if getattr(sys, 'frozen', False):
    BASEDIR = sys._MEIPASS
else:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_DIRECTORY = os.getcwd()

init_yaml_representer()

DOC_FILE = '../README.md'
DEFAULT_CONFIG_FILE = './config.yml'
DEFAULT_OUPUT_DIRNAME = 'helm-fine-upgrade'
RUNTIME_MANIFESTS_FILENAME = 'runtime_manifests.yaml'
RENDERED_MANIFESTS_FILENAME = 'rendered_manifests.yaml'

def diff(chart_path: str,
         release_name: str,
         values: str,
         output_path: str,
         config_path: str,
         selector: str) -> None:
    """根据 helm template 生成的 yaml 文件，拉取集群对象配置，并过滤掉无关字段，生成易于对比的 yaml 文件

    Args:
        chart_path (str): Chart 路径
        release_name (str): Release name
        values (str): values.yaml 文件路径
        output_path (str): 输出内容目录路径
        config_path (str): 自定义配置文件路径
    """
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = yaml.safe_load(config_file)

    shell_cmd = f'helm template --is-upgrade --no-hooks --skip-crds {release_name} {chart_path}'
    if values is not None:
        shell_cmd += f' -f {values}'
    print('执行 helm template 命令...')
    cmd_output = run_shell_cmd(shell_cmd)
    release_original_manifests_generator = yaml.safe_load_all(cmd_output)
    # 提取所有 Release 接管的集群中的 manifest
    cluster_original_manifests = get_all_release_api_objects(release_name)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)
    rendered_original_manifests = []
    manifest_key_set = set() # 与 release 中 manifest 匹配的 cluster 中的 manifest key
    rendered_manifest_dict = {}
    service_unique_keys = []
    for rendered_manifest in release_original_manifests_generator:
        rendered_original_manifests.append(rendered_manifest) # 第一次遍历生成器时，把 manifest 另外存入 list
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        rendered_manifest_dict[manifest_unique_key] = rendered_manifest # 将 rendered_original_manifest 转成字典
        if manifest_unique_key in cluster_manifest_dict:
            manifest_key_set.add(manifest_unique_key)
        if rendered_manifest['kind'] == 'Service':
            service_unique_keys.append(manifest_unique_key)

    # 集群中 Release 接管的，但又不在当前 release 中的对象 manifest key
    extra_manifest_key_set = set(cluster_manifest_dict.keys()) - manifest_key_set
    # print(extra_manifest_key_set)

    selector_dict = parse_selector(selector)
    if bool(selector_dict):
        direct_selector_rendered_manifests = [rendered_manifest for rendered_manifest in rendered_original_manifests if is_manifest_match_selector(rendered_manifest, selector)]
        selector_rendered_manifests = find_and_merge_related_rendered_manifests_of_deployments(direct_selector_rendered_manifests, rendered_manifest_dict, service_unique_keys)
    else:
        selector_rendered_manifests = rendered_original_manifests

    print('开始逐一对比API对象配置...')
    cluster_manifests = []
    release_manifests = []
    for rendered_manifest in selector_rendered_manifests:
        # 过滤掉影响对比的字段
        remove_ignore_fields(rendered_manifest, config['ignore_fields'])
        release_manifests.append(rendered_manifest)
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        # 寻找与 release manifest 匹配的集群中的 manifest
        if manifest_unique_key in cluster_manifest_dict:
            # 完全匹配的 manifest
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
        else:
            # 到集群中直接查找
            cluster_manifest = get_api_object_spec(rendered_manifest['kind'], rendered_manifest['metadata']['name'],
                                        namespace=rendered_manifest['metadata']['namespace'] if 'namespace' in rendered_manifest['metadata'] else None)
            if cluster_manifest is None:
                # 从 extra_manifest_key_set 中查找仅尾部 hash 不同的对象
                same_manifest_key = find_first_same_object_key_with_different_hash(extra_manifest_key_set, manifest_unique_key)
                if same_manifest_key is None:
                    continue
                extra_manifest_key_set.remove(same_manifest_key)
                cluster_manifest = cluster_manifest_dict[same_manifest_key]
        # 过滤掉影响对比的字段
        remove_ignore_fields(cluster_manifest, config['ignore_fields'])
        cluster_manifests.append(cluster_manifest)

    # 未使用选择器时，将集群中额外的 manifest 放到最后面
    if not bool(selector_dict):
        # 把剩下的 extra_manifest_key_set 中没有匹配到的对象放到末尾
        for manifest_unique_key in extra_manifest_key_set:
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
            remove_ignore_fields(cluster_manifest, config['ignore_fields'])
            cluster_manifests.append(cluster_manifest)

    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, RENDERED_MANIFESTS_FILENAME), 'w', encoding='utf-8') as outfile:
        yaml.dump_all(release_manifests, outfile, allow_unicode=True)
    print(f'生成文件: {os.path.join(output_path, RENDERED_MANIFESTS_FILENAME)}.')
    with open(os.path.join(output_path, RUNTIME_MANIFESTS_FILENAME), 'w', encoding='utf-8') as outfile:
        yaml.dump_all(cluster_manifests, outfile, allow_unicode=True)
    print(f'生成文件: {os.path.join(output_path, RUNTIME_MANIFESTS_FILENAME)}.')

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
            # related_rendered_manifests.append(rendered_manifest_dict[namespace_unique_key])
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
