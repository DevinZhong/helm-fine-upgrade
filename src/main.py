#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
import argparse
import yaml
from utils.yaml_utils import init_yaml_representer
from utils.shell_utils import run_shell_cmd
from utils.dict_utils import remove_ignore_fields
from utils.helm_utils import get_api_object_spec, get_all_release_api_objects, manifests_list_to_dict, get_manifest_unique_key

if getattr(sys, 'frozen', False):
    BASEDIR = sys._MEIPASS
else:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_DIRECTORY = os.getcwd()

init_yaml_representer()

DEFAULT_CONFIG_FILE = './config.yml'
DEFAULT_OUPUT_DIRNAME = 'helm-cluster-diff'
CLUSTER_DUMP_FILENAME = 'cluster_manifests.yaml'
RELEASE_CONTENT_FILENAME = 'release_manifests.yaml'


def diff(chart_path: str,
         release_name: str,
         release_namespace: str,
         values: str,
         output_path: str,
         config_path: str,
         kubeconfig: str,
         debug: bool) -> None:
    """根据 helm template 生成的 yaml 文件，拉取集群对象配置，并过滤掉无关字段，生成易于对比的 yaml 文件

    Args:
        chart_path (str): Chart 路径
        release_name (str): Release name
        release_namespace (str): Release namespace
        values (str): values.yaml 文件路径
        output_path (str): 输出内容目录路径
        config_path (str): 自定义配置文件路径
        kubeconfig (str): 集群连接信息文件路径
        debug (bool): 是否为调试模式
    """
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = yaml.safe_load(config_file)

    shell_cmd = f'helm template --is-upgrade --no-hooks --skip-crds -n {release_namespace} {release_name} {chart_path}'
    if values is not None:
        shell_cmd += f' -f {values}'
    print('执行 helm template 命令...')
    cmd_output = run_shell_cmd(shell_cmd, debug)
    release_original_manifests = yaml.safe_load_all(cmd_output)
    
    cluster_original_manifests = get_all_release_api_objects(release_name, release_namespace, kubeconfig, debug)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)

    print('开始逐一对比API对象配置...')
    cluster_manifests = []
    release_manifests = []
    manifest_key_set = set()
    for release_manifest in release_original_manifests:
        remove_ignore_fields(release_manifest, config['ignore_fields'])
        release_manifests.append(release_manifest)
        manifest_unique_key = get_manifest_unique_key(release_manifest)
        if manifest_unique_key in cluster_manifest_dict:
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
            manifest_key_set.add(manifest_unique_key)
        else:
            cluster_manifest = get_api_object_spec(release_manifest['kind'], release_manifest['metadata']['name'],
                                        namespace=release_manifest['metadata']['namespace'] if 'namespace' in release_manifest['metadata'] else None,
                                        kubeconfig=kubeconfig, debug=debug)
        if cluster_manifest is None:
            continue
        remove_ignore_fields(cluster_manifest, config['ignore_fields'])
        cluster_manifests.append(cluster_manifest)

    for cluster_manifest in cluster_original_manifests:
        manifest_unique_key = get_manifest_unique_key(cluster_manifest)
        if manifest_unique_key not in manifest_key_set:
            cluster_manifests.append(cluster_manifest)

    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, RELEASE_CONTENT_FILENAME), 'w', encoding='utf-8') as outfile:
        yaml.dump_all(release_manifests, outfile, allow_unicode=True)
    print(f'生成文件: {os.path.join(output_path, RELEASE_CONTENT_FILENAME)}.')
    with open(os.path.join(output_path, CLUSTER_DUMP_FILENAME), 'w', encoding='utf-8') as outfile:
        yaml.dump_all(cluster_manifests, outfile, allow_unicode=True)
    print(f'生成文件: {os.path.join(output_path, CLUSTER_DUMP_FILENAME)}.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', type=str, help='执行的操作，目前支持3种操作：diff、update_ownership、show_default_config')
    parser.add_argument('--release_name', type=str, default='', help='Release Name')
    parser.add_argument('--release_namespace', type=str, default='default', help='Release Namespace')
    parser.add_argument('--chart_path', type=str, help='chart 路径，可以是chart包或者源代码目录')
    parser.add_argument('--values', type=str, help='自定义 values 文件路径')
    parser.add_argument('--output_path', type=str, default=os.path.join(CURRENT_DIRECTORY, DEFAULT_OUPUT_DIRNAME), help='输出比对文件的目录')
    parser.add_argument('--kubeconfig', type=str, help='集群配置文件路径')
    parser.add_argument('--config_path', type=str, default=os.path.join(BASEDIR, DEFAULT_CONFIG_FILE), help='自定义脚本配置文件路径')
    parser.add_argument('--dry_run', nargs='?', const=True, type=bool, help='仅模拟运行，不实际变更集群，update_ownership 操作可使用')
    parser.add_argument('--debug', nargs='?', const=True, type=bool, help='是否打印 SHELL 命令')
    args = parser.parse_args()

    diff(chart_path=args.chart_path,
            release_name=args.release_name,
            release_namespace=args.release_namespace,
            values=args.values,
            output_path=args.output_path,
            config_path=args.config_path,
            kubeconfig=args.kubeconfig,
            debug=args.debug)
