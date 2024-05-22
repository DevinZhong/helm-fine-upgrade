#!/usr/bin/env python
#-*- coding:utf-8 -*-
 
import yaml
from ruamel.yaml import YAML
from utils.shell_utils import run_shell_cmd
from utils.helm_utils import get_api_object_spec, get_image_version
from utils.dict_utils import set_value
from utils.helm_utils import get_api_object_spec, get_all_release_api_objects, manifests_list_to_dict, get_manifest_unique_key


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

    shell_cmd = f'helm template --is-upgrade --no-hooks --skip-crds {release_name} {chart_path}'
    if values is not None:
        shell_cmd += f' -f {values}'
    print('执行 helm template 命令...')
    cmd_output = run_shell_cmd(shell_cmd)
    release_original_manifests = yaml.safe_load_all(cmd_output)
    
    cluster_original_manifests = get_all_release_api_objects(release_name)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)

    print('开始逐一对比Deployment对象镜像版本...')
    different_image_dict = {}
    for release_manifest in release_original_manifests:
        kind = release_manifest['kind']
        if kind != 'Deployment':
            continue
        name = release_manifest['metadata']['name']
        namespace = release_manifest['metadata']['namespace'] if 'namespace' in release_manifest['metadata'] else None
        manifest_unique_key = get_manifest_unique_key(release_manifest)
        if manifest_unique_key in cluster_manifest_dict:
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
        else:
            cluster_manifest = get_api_object_spec('Deployment', name, namespace=namespace)
        if cluster_manifest is None:
            continue

        release_version = get_image_version(release_manifest)
        cluster_version = get_image_version(cluster_manifest)
        if release_version == cluster_version:
            continue
        elif name in config['image_version_fields']:
            values_field_paths = config['image_version_fields'][name]
            set_value(different_image_dict, values_field_paths, cluster_version)
            set_value(values_content, values_field_paths, cluster_version)

    if dry_run:
        print('镜像版本差异：')
        print(yaml.dump(different_image_dict, allow_unicode=True))
    else:
        with open(values, 'w', encoding='utf-8') as values_file:
            ruamel_yaml.dump(values_content, values_file)
        print(f'已更新文件：{values}.')
