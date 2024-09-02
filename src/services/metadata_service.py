#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import yaml
from utils.shell_utils import run_shell_cmd
from utils.helm_utils import get_api_object_spec, get_all_release_api_objects, manifests_list_to_dict, get_manifest_unique_key, is_manifest_match_selector

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
    rendered_original_manifest = yaml.safe_load_all(cmd_output)
    
    cluster_original_manifests = get_all_release_api_objects(release_name)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)

    print('开始逐一检查API对象配置...')
    set_metadata_commands = []
    for rendered_manifest in rendered_original_manifest:
        # 如果与选择器不匹配，直接跳过
        if not is_manifest_match_selector(rendered_manifest, selector):
            continue

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
