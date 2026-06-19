#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
import copy
import yaml
from utils.yaml_utils import init_yaml_representer
from utils.shell_utils import run_cmd
from utils.dict_utils import remove_ignore_fields, parse_selector
from utils.output_utils import (
    exit_if_fail_on_triggered,
    print_status,
    print_structured_output,
)
from utils.helm_utils import (
    build_helm_template_cmd,
    get_api_object_spec,
    get_all_release_api_objects,
    get_release_manifests,
    manifests_list_to_dict,
    get_manifest_namespace,
    get_manifest_unique_key,
    find_first_same_object_key_with_different_hash,
    is_manifest_match_selector
    )   
from utils.manifest_utils import find_and_merge_related_rendered_manifests_of_deployments
from utils.kube_ops_utils import apply_manifests

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

IMMUTABLE_FIELD_PATHS = {
    'Deployment': ['spec.selector'],
    'StatefulSet': ['spec.selector', 'spec.serviceName'],
    'DaemonSet': ['spec.selector'],
    'Service': ['spec.clusterIP', 'spec.clusterIPs', 'spec.ipFamilies',
                'spec.ipFamilyPolicy'],
    'PersistentVolumeClaim': ['spec.storageClassName'],
}

def get_field_value(dictionary: dict, field_path: str):
    value = dictionary
    for key in field_path.split('.'):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value

def render_chart_manifests(chart_path: str, release_name: str, values: str) -> list:
    print_status('执行 helm template 命令...')
    cmd_output = run_cmd(build_helm_template_cmd(release_name, chart_path, values))
    if cmd_output is None:
        return None
    return [manifest for manifest in yaml.safe_load_all(cmd_output)
            if manifest is not None]

def select_rendered_manifests(rendered_manifests: list, selector: str) -> list:
    rendered_manifest_dict = {}
    service_unique_keys = []
    for rendered_manifest in rendered_manifests:
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        rendered_manifest_dict[manifest_unique_key] = rendered_manifest
        if rendered_manifest.get('kind') == 'Service':
            service_unique_keys.append(manifest_unique_key)

    selector_dict = parse_selector(selector)
    if bool(selector_dict):
        direct_selector_rendered_manifests = [
            rendered_manifest for rendered_manifest in rendered_manifests
            if is_manifest_match_selector(rendered_manifest, selector)
        ]
        return find_and_merge_related_rendered_manifests_of_deployments(
            direct_selector_rendered_manifests, rendered_manifest_dict,
            service_unique_keys)
    return rendered_manifests

def normalize_manifest_for_compare(manifest: dict, ignore_fields_config: dict) -> dict:
    normalized_manifest = copy.deepcopy(manifest)
    remove_ignore_fields(normalized_manifest, ignore_fields_config)
    return normalized_manifest

def manifests_are_equal(left: dict, right: dict, ignore_fields_config: dict) -> bool:
    normalized_left = normalize_manifest_for_compare(left, ignore_fields_config)
    normalized_right = normalize_manifest_for_compare(right, ignore_fields_config)
    return yaml.dump(normalized_left, allow_unicode=True, sort_keys=True) == \
        yaml.dump(normalized_right, allow_unicode=True, sort_keys=True)

def detect_immutable_field_changes(rendered_manifest: dict,
                                   cluster_manifest: dict) -> list:
    kind = rendered_manifest.get('kind')
    changes = []
    for field_path in IMMUTABLE_FIELD_PATHS.get(kind, []):
        rendered_value = get_field_value(rendered_manifest, field_path)
        cluster_value = get_field_value(cluster_manifest, field_path)
        if rendered_value != cluster_value:
            changes.append(field_path)
    return changes

def build_upgrade_plan(rendered_manifests: list,
                       cluster_manifests: list,
                       config: dict,
                       selector: str = '',
                       lookup_manifest_func=get_api_object_spec) -> dict:
    """Build a structured upgrade plan without changing cluster state."""
    selected_rendered_manifests = select_rendered_manifests(
        rendered_manifests, selector)
    cluster_manifest_dict = manifests_list_to_dict(cluster_manifests)
    selected_key_set = {get_manifest_unique_key(manifest)
                        for manifest in selected_rendered_manifests}
    matched_cluster_keys = set()
    extra_manifest_key_set = set(cluster_manifest_dict.keys()) - selected_key_set
    ignore_fields_config = config.get('ignore_fields', {})

    plan = {
        'summary': {
            'create': 0,
            'update': 0,
            'unchanged': 0,
            'adopt': 0,
            'orphan': 0,
            'immutable_risk': 0,
        },
        'resources': [],
    }

    for rendered_manifest in selected_rendered_manifests:
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        status = 'create'
        cluster_manifest = None
        matched_cluster_key = None

        if manifest_unique_key in cluster_manifest_dict:
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
            matched_cluster_key = manifest_unique_key
            status = 'unchanged' if manifests_are_equal(
                rendered_manifest, cluster_manifest, ignore_fields_config) else 'update'
        else:
            cluster_manifest = lookup_manifest_func(
                rendered_manifest['kind'],
                rendered_manifest['metadata']['name'],
                namespace=rendered_manifest['metadata'].get('namespace'))
            if cluster_manifest is not None:
                status = 'adopt'
            else:
                same_manifest_key = find_first_same_object_key_with_different_hash(
                    extra_manifest_key_set, manifest_unique_key)
                if same_manifest_key is not None:
                    cluster_manifest = cluster_manifest_dict[same_manifest_key]
                    matched_cluster_key = same_manifest_key
                    status = 'update'

        immutable_field_changes = []
        if cluster_manifest is not None:
            immutable_field_changes = detect_immutable_field_changes(
                rendered_manifest, cluster_manifest)
            if matched_cluster_key is not None:
                matched_cluster_keys.add(matched_cluster_key)
                extra_manifest_key_set.discard(matched_cluster_key)

        if immutable_field_changes:
            plan['summary']['immutable_risk'] += 1

        plan['summary'][status] += 1
        resource_plan = {
            'key': manifest_unique_key,
            'kind': rendered_manifest['kind'],
            'namespace': rendered_manifest['metadata'].get('namespace', ''),
            'name': rendered_manifest['metadata']['name'],
            'status': status,
        }
        if matched_cluster_key is not None and matched_cluster_key != manifest_unique_key:
            resource_plan['matched_runtime_key'] = matched_cluster_key
        if immutable_field_changes:
            resource_plan['immutable_field_changes'] = immutable_field_changes
        plan['resources'].append(resource_plan)

    if not bool(parse_selector(selector)):
        for manifest_unique_key in sorted(extra_manifest_key_set - matched_cluster_keys):
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
            plan['summary']['orphan'] += 1
            plan['resources'].append({
                'key': manifest_unique_key,
                'kind': cluster_manifest['kind'],
                'namespace': cluster_manifest['metadata'].get('namespace', ''),
                'name': cluster_manifest['metadata']['name'],
                'status': 'orphan',
            })

    return plan

def plan_upgrade(chart_path: str,
                 release_name: str,
                 values: str,
                 config_path: str,
                 selector: str,
                 output_format: str = 'yaml',
                 fail_on: str = '') -> None:
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = yaml.safe_load(config_file)

    rendered_manifests = render_chart_manifests(chart_path, release_name, values)
    if rendered_manifests is None:
        return
    cluster_manifests = get_all_release_api_objects(release_name)
    plan = build_upgrade_plan(rendered_manifests, cluster_manifests, config,
                              selector=selector)
    print_structured_output(plan, output_format)
    exit_if_fail_on_triggered(plan, fail_on)

def manifest_info(manifest: dict, status: str) -> dict:
    return {
        'key': get_manifest_unique_key(manifest),
        'kind': manifest['kind'],
        'namespace': get_manifest_namespace(manifest),
        'name': manifest['metadata']['name'],
        'status': status,
    }

def compare_manifest_sets(left_manifests: list,
                          right_manifests: list,
                          left_label: str,
                          right_label: str,
                          ignore_fields_config: dict) -> dict:
    left_manifest_dict = manifests_list_to_dict(left_manifests)
    right_manifest_dict = manifests_list_to_dict(right_manifests)
    left_keys = set(left_manifest_dict.keys())
    right_keys = set(right_manifest_dict.keys())
    common_keys = left_keys & right_keys

    missing_from_right = []
    extra_in_right = []
    changed = []

    for key in sorted(left_keys - right_keys):
        missing_from_right.append(manifest_info(
            left_manifest_dict[key], f'missing_from_{right_label}'))

    for key in sorted(right_keys - left_keys):
        extra_in_right.append(manifest_info(
            right_manifest_dict[key], f'extra_in_{right_label}'))

    for key in sorted(common_keys):
        if not manifests_are_equal(left_manifest_dict[key],
                                   right_manifest_dict[key],
                                   ignore_fields_config):
            changed.append({
                'key': key,
                'kind': left_manifest_dict[key]['kind'],
                'namespace': get_manifest_namespace(left_manifest_dict[key]),
                'name': left_manifest_dict[key]['metadata']['name'],
                'status': f'{left_label}_{right_label}_drift',
            })

    return {
        f'missing_from_{right_label}': missing_from_right,
        f'extra_in_{right_label}': extra_in_right,
        'changed': changed,
    }

def build_state_check(release_manifests: list,
                      runtime_manifests: list,
                      chart_manifests: list,
                      config: dict) -> dict:
    ignore_fields_config = config.get('ignore_fields', {})
    runtime_consistency = compare_manifest_sets(
        release_manifests, runtime_manifests, 'release', 'runtime',
        ignore_fields_config)
    state_check = {
        'summary': {
            'release_resources': len(release_manifests or []),
            'runtime_resources': len(runtime_manifests or []),
            'chart_resources': len(chart_manifests or []) if chart_manifests is not None else None,
            'runtime_missing': len(runtime_consistency['missing_from_runtime']),
            'runtime_extra': len(runtime_consistency['extra_in_runtime']),
            'runtime_drift': len(runtime_consistency['changed']),
            'chart_create': 0,
            'chart_update': 0,
            'chart_delete': 0,
        },
        'runtime_consistency': runtime_consistency,
    }

    if chart_manifests is not None:
        chart_consistency = compare_manifest_sets(
            release_manifests, chart_manifests, 'release', 'chart',
            ignore_fields_config)
        state_check['summary']['chart_create'] = len(
            chart_consistency['extra_in_chart'])
        state_check['summary']['chart_update'] = len(
            chart_consistency['changed'])
        state_check['summary']['chart_delete'] = len(
            chart_consistency['missing_from_chart'])
        state_check['chart_consistency'] = chart_consistency

    return state_check

def state_check(release_name: str,
                chart_path: str,
                values: str,
                config_path: str,
                output_format: str = 'yaml',
                fail_on: str = '') -> None:
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = yaml.safe_load(config_file)

    release_manifests = get_release_manifests(release_name)
    if release_manifests is None:
        return
    runtime_manifests = get_all_release_api_objects(release_name)
    chart_manifests = None
    if chart_path is not None:
        chart_manifests = render_chart_manifests(chart_path, release_name, values)
        if chart_manifests is None:
            return

    result = build_state_check(release_manifests, runtime_manifests,
                               chart_manifests, config)
    print_structured_output(result, output_format)
    exit_if_fail_on_triggered(result, fail_on)

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

    print('执行 helm template 命令...')
    cmd_output = run_cmd(build_helm_template_cmd(release_name, chart_path, values))
    if cmd_output is None:
        return
    rendered_original_manifests_generator = yaml.safe_load_all(cmd_output)
    # 提取所有 Release 接管的集群中的 manifest
    cluster_original_manifests = get_all_release_api_objects(release_name)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)
    rendered_original_manifests = []
    manifest_key_set = set() # 与 release 中 manifest 匹配的 cluster 中的 manifest key
    rendered_manifest_dict = {}
    service_unique_keys = []
    for rendered_manifest in rendered_original_manifests_generator:
        if rendered_manifest is None:
            continue
        rendered_original_manifests.append(rendered_manifest) # 第一次遍历生成器时，把 manifest 另外存入 list
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        rendered_manifest_dict[manifest_unique_key] = rendered_manifest # 将 rendered_original_manifest 转成字典
        if manifest_unique_key in cluster_manifest_dict:
            manifest_key_set.add(manifest_unique_key)
        if rendered_manifest.get('kind') == 'Service':
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
    rendered_manifests = []
    for rendered_manifest in selector_rendered_manifests:
        # 过滤掉影响对比的字段
        remove_ignore_fields(rendered_manifest, config['ignore_fields'])
        rendered_manifests.append(rendered_manifest)
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
        yaml.dump_all(rendered_manifests, outfile, allow_unicode=True)
    print(f'生成文件: {os.path.join(output_path, RENDERED_MANIFESTS_FILENAME)}.')
    with open(os.path.join(output_path, RUNTIME_MANIFESTS_FILENAME), 'w', encoding='utf-8') as outfile:
        yaml.dump_all(cluster_manifests, outfile, allow_unicode=True)
    print(f'生成文件: {os.path.join(output_path, RUNTIME_MANIFESTS_FILENAME)}.')

def apply_upgrade(chart_path: str,
         release_name: str,
         values: str,
         selector: str) -> None:
    """使用 kubectl apply 更新关联的 manifest

    Args:
        chart_path (str): Chart 路径
        release_name (str): Release name
        values (str): values.yaml 文件路径
        output_path (str): 输出内容目录路径
        config_path (str): 自定义配置文件路径
    """

    print('执行 helm template 命令...')
    cmd_output = run_cmd(build_helm_template_cmd(release_name, chart_path, values))
    if cmd_output is None:
        return
    rendered_original_manifests_generator = yaml.safe_load_all(cmd_output)
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

    if os.environ.get('DRY_RUN_FLAG', '0') == '1':
        print('Manifests will apply:')
        print(yaml.dump_all(selector_rendered_manifests, allow_unicode=True))
    else:
        apply_manifests(selector_rendered_manifests)
