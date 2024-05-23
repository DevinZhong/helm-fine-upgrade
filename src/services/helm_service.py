#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
import yaml
from utils.yaml_utils import init_yaml_representer
from utils.shell_utils import run_shell_cmd
from utils.dict_utils import remove_ignore_fields
from utils.helm_utils import get_api_object_spec, get_all_release_api_objects, manifests_list_to_dict, get_manifest_unique_key, find_first_same_object_key_with_different_hash

if getattr(sys, 'frozen', False):
    BASEDIR = sys._MEIPASS
else:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_DIRECTORY = os.getcwd()

init_yaml_representer()

DOC_FILE = '../README.md'
DEFAULT_CONFIG_FILE = './config.yml'
DEFAULT_OUPUT_DIRNAME = 'helm-cluster-diff'
CLUSTER_DUMP_FILENAME = 'cluster_manifests.yaml'
RELEASE_CONTENT_FILENAME = 'release_manifests.yaml'

def diff(chart_path: str,
         release_name: str,
         values: str,
         output_path: str,
         config_path: str) -> None:
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
    release_original_manifests = []
    manifest_key_set = set() # 与 release 中 manifest 匹配的 cluster 中的 manifest key
    for release_manifest in release_original_manifests_generator:
        release_original_manifests.append(release_manifest) # 第一次遍历生成器时，把 manifest 另外存入 list
        manifest_unique_key = get_manifest_unique_key(release_manifest)
        if manifest_unique_key in cluster_manifest_dict:
            manifest_key_set.add(manifest_unique_key)

    # 集群中 Release 接管的，但又不在当前 release 中的对象 manifest key
    extra_manifest_key_set = set(cluster_manifest_dict.keys()) - manifest_key_set
    print(extra_manifest_key_set)

    print('开始逐一对比API对象配置...')
    cluster_manifests = []
    release_manifests = []
    for release_manifest in release_original_manifests:
        # 过滤掉影响对比的字段
        remove_ignore_fields(release_manifest, config['ignore_fields'])
        release_manifests.append(release_manifest)
        manifest_unique_key = get_manifest_unique_key(release_manifest)
        # 寻找与 release manifest 匹配的集群中的 manifest
        if manifest_unique_key in cluster_manifest_dict:
            # 完全匹配的 manifest
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
        else:
            # 到集群中直接查找
            cluster_manifest = get_api_object_spec(release_manifest['kind'], release_manifest['metadata']['name'],
                                        namespace=release_manifest['metadata']['namespace'] if 'namespace' in release_manifest['metadata'] else None)
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

    # 把剩下的 extra_manifest_key_set 中没有匹配到的对象放到末尾
    for manifest_unique_key in extra_manifest_key_set:
        cluster_manifest = cluster_manifest_dict[manifest_unique_key]
        remove_ignore_fields(cluster_manifest, config['ignore_fields'])
        cluster_manifests.append(cluster_manifest)

    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, RELEASE_CONTENT_FILENAME), 'w', encoding='utf-8') as outfile:
        yaml.dump_all(release_manifests, outfile, allow_unicode=True)
    print(f'生成文件: {os.path.join(output_path, RELEASE_CONTENT_FILENAME)}.')
    with open(os.path.join(output_path, CLUSTER_DUMP_FILENAME), 'w', encoding='utf-8') as outfile:
        yaml.dump_all(cluster_manifests, outfile, allow_unicode=True)
    print(f'生成文件: {os.path.join(output_path, CLUSTER_DUMP_FILENAME)}.')