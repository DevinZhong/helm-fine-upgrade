#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import yaml
from utils.shell_utils import run_shell_cmd
from utils.dict_utils import parse_selector
from utils.helm_utils import get_api_object_spec, get_all_release_api_objects, manifests_list_to_dict, get_manifest_unique_key, is_manifest_match_selector
from utils.manifest_utils import find_and_merge_related_rendered_manifests_of_deployments

HELM_NAMESPACE = os.environ.get('HELM_NAMESPACE')

def set_ownership_metadata(chart_path: str,
                           release_name: str,
                           values: str,
                           selector: str, 
                           dry_run: str) -> None:
    """
    设置集群对象的元数据，以支持 helm 修改非 helm 管理的对象
    """
    shell_cmd = f'helm template --is-upgrade --no-hooks --skip-crds {release_name} {chart_path}'
    if values is not None:
        shell_cmd += f' -f {values}'
    print('执行 helm template 命令...')
    cmd_output = run_shell_cmd(shell_cmd)
    release_original_manifests_generator = yaml.safe_load_all(cmd_output)
    
    cluster_original_manifests = get_all_release_api_objects(release_name)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)

    rendered_original_manifests = []
    rendered_manifest_dict = {}
    service_unique_keys = []
    for rendered_manifest in release_original_manifests_generator:
        rendered_original_manifests.append(rendered_manifest) # 第一次遍历生成器时，把 manifest 另外存入 list
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        rendered_manifest_dict[manifest_unique_key] = rendered_manifest # 将 rendered_original_manifest 转成字典
        if rendered_manifest['kind'] == 'Service':
            service_unique_keys.append(manifest_unique_key)

    selector_dict = parse_selector(selector)
    if bool(selector_dict):
        direct_selector_rendered_manifests = [rendered_manifest for rendered_manifest in rendered_original_manifests if is_manifest_match_selector(rendered_manifest, selector)]
        selector_rendered_manifests = find_and_merge_related_rendered_manifests_of_deployments(direct_selector_rendered_manifests, rendered_manifest_dict, service_unique_keys)
    else:
        selector_rendered_manifests = rendered_original_manifests

    print('开始逐一检查API对象配置...')
    set_metadata_commands = []
    for rendered_manifest in selector_rendered_manifests:
        kind = rendered_manifest['kind']
        name = rendered_manifest['metadata']['name']
        namespace = rendered_manifest['metadata']['namespace'] if 'namespace' in rendered_manifest['metadata'] else None
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        if manifest_unique_key in cluster_manifest_dict:
            continue
        else:
            cluster_manifest = get_api_object_spec(kind, name, namespace=namespace)
            if cluster_manifest is None:
                continue
        cmds = []
        if not 'annotations' in cluster_manifest['metadata'] \
            or not 'meta.helm.sh/release-name' in cluster_manifest['metadata']['annotations'] \
            or cluster_manifest['metadata']['annotations']['meta.helm.sh/release-name'] != release_name:
            cmds.append(f'kubectl annotate {kind} {name} meta.helm.sh/release-name={release_name} --overwrite')
        if not 'annotations' in cluster_manifest['metadata'] \
            or not 'meta.helm.sh/release-namespace' in cluster_manifest['metadata']['annotations'] \
            or cluster_manifest['metadata']['annotations']['meta.helm.sh/release-namespace'] != HELM_NAMESPACE:
            cmds.append(f'kubectl annotate {kind} {name} meta.helm.sh/release-namespace={HELM_NAMESPACE} --overwrite')
        if not 'labels' in cluster_manifest['metadata'] \
            or not 'app.kubernetes.io/managed-by' in cluster_manifest['metadata']['labels'] \
            or cluster_manifest['metadata']['labels']['app.kubernetes.io/managed-by'] != 'Helm':
            cmds.append(f'kubectl label {kind} {name} app.kubernetes.io/managed-by=Helm --overwrite')
        if namespace is not None:
            cmds = [cmd + f' -n {namespace}' for cmd in cmds]
        set_metadata_commands.extend(cmds)

    if dry_run:
        print('commands will run:')
        print('\n'.join(set_metadata_commands))
    else:
        print('开始逐一执行变更命令...')
        for cmd in set_metadata_commands:
            print(run_shell_cmd(cmd))
