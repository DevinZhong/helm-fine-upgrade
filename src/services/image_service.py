#!/usr/bin/env python
#-*- coding:utf-8 -*-

import yaml
from ruamel.yaml import YAML
from utils.shell_utils import run_cmd
from utils.dict_utils import set_value
from utils.helm_utils import (build_helm_template_cmd, get_api_object_spec,
                              get_all_release_api_objects,
                              get_manifest_unique_key, get_image_version,
                              manifests_list_to_dict)


# ruamel 可以最大化保留原文件格式，这里用于修改 values.yaml 文件内容
ruamel_yaml = YAML()
ruamel_yaml.preserve_quotes = True

def image_version_diff(chart_path: str,
                       release_name: str,
                       values: str,
                       config_path: str,
                       dry_run: str) -> None:
    """根据 helm template 生成的 yaml 文件，拉取集群对象配置，输出有差异的镜像版本，或直接更新 values 文件

    Args:
        chart_path (str): Chart 路径
        release_name (str): Release name
        values (str): values.yaml 文件路径
        config_path (str): 自定义配置文件路径
        dry_run (str): 不真正运行
    """
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = yaml.safe_load(config_file)

    with open(values, 'r', encoding='utf-8') as values_file:
        values_content = ruamel_yaml.load(values_file)

    print('执行 helm template 命令...')
    cmd_output = run_cmd(build_helm_template_cmd(release_name, chart_path, values))
    if cmd_output is None:
        return
    rendered_original_manifest = yaml.safe_load_all(cmd_output)
    
    cluster_original_manifests = get_all_release_api_objects(release_name)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)

    print('开始逐一对比Deployment对象镜像版本...')
    different_image_dict = {}
    for rendered_manifest in rendered_original_manifest:
        if rendered_manifest is None:
            continue
        kind = rendered_manifest['kind']
        if kind != 'Deployment':
            continue
        name = rendered_manifest['metadata']['name']
        namespace = rendered_manifest['metadata']['namespace'] if 'namespace' in rendered_manifest['metadata'] else None
        manifest_unique_key = get_manifest_unique_key(rendered_manifest)
        if manifest_unique_key in cluster_manifest_dict:
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
        else:
            cluster_manifest = get_api_object_spec('Deployment', name, namespace=namespace)
        if cluster_manifest is None:
            continue

        release_version = get_image_version(rendered_manifest)
        cluster_version = get_image_version(cluster_manifest)
        if release_version == cluster_version:
            continue
        image_version_fields = config.get('image_version_fields') or {}
        if name in image_version_fields:
            values_field_paths = image_version_fields[name]
            set_value(different_image_dict, values_field_paths, cluster_version)
            set_value(values_content, values_field_paths, cluster_version)

    if dry_run:
        print('镜像版本差异：')
        print(yaml.dump(different_image_dict, allow_unicode=True))
    else:
        with open(values, 'w', encoding='utf-8') as values_file:
            ruamel_yaml.dump(values_content, values_file)
        print(f'已更新文件：{values}.')
