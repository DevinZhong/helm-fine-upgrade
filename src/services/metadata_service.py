#!/usr/bin/env python
#-*- coding:utf-8 -*-

import yaml
from utils.shell_utils import run_cmd
from utils.dict_utils import parse_selector
from utils.helm_utils import (build_helm_template_cmd, build_kubectl_cmd,
                              get_api_object_spec, get_all_release_api_objects,
                              get_helm_namespace,
                              get_manifest_namespace,
                              manifests_list_to_dict, get_manifest_unique_key,
                              is_manifest_match_selector)
from utils.manifest_utils import find_and_merge_related_rendered_manifests_of_deployments

def get_manifest_lookup_namespace(manifest: dict):
    namespace = get_manifest_namespace(manifest)
    return namespace if namespace else None

def get_ownership_metadata(manifest: dict) -> dict:
    metadata = manifest.get('metadata', {})
    annotations = metadata.get('annotations', {}) or {}
    labels = metadata.get('labels', {}) or {}
    return {
        'release_name': annotations.get('meta.helm.sh/release-name'),
        'release_namespace': annotations.get('meta.helm.sh/release-namespace'),
        'managed_by': labels.get('app.kubernetes.io/managed-by'),
    }

def build_set_ownership_commands(kind: str,
                                 name: str,
                                 namespace: str,
                                 release_name: str,
                                 release_namespace: str) -> list:
    cmds = [
        ['annotate', kind, name,
         f'meta.helm.sh/release-name={release_name}', '--overwrite'],
        ['annotate', kind, name,
         f'meta.helm.sh/release-namespace={release_namespace}', '--overwrite'],
        ['label', kind, name,
         'app.kubernetes.io/managed-by=Helm', '--overwrite'],
    ]
    if namespace:
        cmds = [cmd + ['-n', namespace] for cmd in cmds]
    return [build_kubectl_cmd(cmd) for cmd in cmds]

def build_adopt_plan(rendered_manifests: list,
                     release_name: str,
                     selector: str = '',
                     lookup_manifest_func=get_api_object_spec) -> dict:
    from services.helm_service import select_rendered_manifests

    release_namespace = get_helm_namespace()
    selected_rendered_manifests = select_rendered_manifests(
        rendered_manifests, selector)
    plan = {
        'summary': {
            'managed': 0,
            'adoptable': 0,
            'needs_metadata_update': 0,
            'conflict': 0,
            'missing': 0,
        },
        'resources': [],
    }

    for rendered_manifest in selected_rendered_manifests:
        kind = rendered_manifest['kind']
        name = rendered_manifest['metadata']['name']
        namespace = get_manifest_namespace(rendered_manifest)
        cluster_manifest = lookup_manifest_func(
            kind, name, namespace=get_manifest_lookup_namespace(rendered_manifest))
        resource_plan = {
            'key': get_manifest_unique_key(rendered_manifest),
            'kind': kind,
            'namespace': namespace,
            'name': name,
        }

        if cluster_manifest is None:
            status = 'missing'
        else:
            ownership = get_ownership_metadata(cluster_manifest)
            resource_plan['current_ownership'] = ownership
            owned_by_current_release = \
                ownership['release_name'] == release_name and \
                ownership['release_namespace'] == release_namespace and \
                ownership['managed_by'] == 'Helm'
            owned_by_other_release = \
                (ownership['release_name'] is not None and
                 ownership['release_name'] != release_name) or \
                (ownership['release_namespace'] is not None and
                 ownership['release_namespace'] != release_namespace)

            if owned_by_current_release:
                status = 'managed'
            elif owned_by_other_release:
                status = 'conflict'
            elif ownership['release_name'] == release_name or \
                    ownership['release_namespace'] == release_namespace or \
                    ownership['managed_by'] == 'Helm':
                status = 'needs_metadata_update'
            else:
                status = 'adoptable'

            if status in ('adoptable', 'needs_metadata_update'):
                resource_plan['commands'] = [
                    ' '.join(cmd) for cmd in build_set_ownership_commands(
                        kind, name, namespace, release_name, release_namespace)
                ]

        resource_plan['status'] = status
        plan['summary'][status] += 1
        plan['resources'].append(resource_plan)

    return plan

def adopt_plan(chart_path: str,
               release_name: str,
               values: str,
               selector: str) -> None:
    print('执行 helm template 命令...')
    cmd_output = run_cmd(build_helm_template_cmd(release_name, chart_path, values))
    if cmd_output is None:
        return
    rendered_manifests = [
        manifest for manifest in yaml.safe_load_all(cmd_output)
        if manifest is not None
    ]
    plan = build_adopt_plan(rendered_manifests, release_name,
                            selector=selector)
    print(yaml.dump(plan, allow_unicode=True, sort_keys=False))

def set_ownership_metadata(chart_path: str,
                           release_name: str,
                           values: str,
                           selector: str, 
                           dry_run: str) -> None:
    """
    设置集群对象的元数据，以支持 helm 修改非 helm 管理的对象
    """
    print('执行 helm template 命令...')
    cmd_output = run_cmd(build_helm_template_cmd(release_name, chart_path, values))
    if cmd_output is None:
        return
    rendered_original_manifests_generator = yaml.safe_load_all(cmd_output)
    
    cluster_original_manifests = get_all_release_api_objects(release_name)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)

    rendered_original_manifests = []
    rendered_manifest_dict = {}
    service_unique_keys = []
    for rendered_manifest in rendered_original_manifests_generator:
        if rendered_manifest is None:
            continue
        rendered_original_manifests.append(rendered_manifest) # 第一次遍历生成器时，把 manifest 另外存入 list
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        rendered_manifest_dict[manifest_unique_key] = rendered_manifest # 将 rendered_original_manifest 转成字典
        if rendered_manifest.get('kind') == 'Service':
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
        namespace = get_manifest_lookup_namespace(rendered_manifest)
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        if manifest_unique_key in cluster_manifest_dict:
            continue
        else:
            cluster_manifest = get_api_object_spec(kind, name, namespace=namespace)
            if cluster_manifest is None:
                continue
        helm_namespace = get_helm_namespace()
        ownership = get_ownership_metadata(cluster_manifest)
        all_cmds = build_set_ownership_commands(
            kind, name, namespace or '', release_name, helm_namespace)
        cmds = []
        if ownership['release_name'] != release_name:
            cmds.append(all_cmds[0])
        if ownership['release_namespace'] != helm_namespace:
            cmds.append(all_cmds[1])
        if ownership['managed_by'] != 'Helm':
            cmds.append(all_cmds[2])
        set_metadata_commands.extend(cmds)

    if dry_run:
        print('commands will run:')
        print('\n'.join([' '.join(cmd) for cmd in set_metadata_commands]))
    else:
        print('开始逐一执行变更命令...')
        for cmd in set_metadata_commands:
            print(run_cmd(cmd))
