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
    release_original_manifests = yaml.safe_load_all(cmd_output)
    
    cluster_original_manifests = get_all_release_api_objects(release_name)
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
                                        namespace=release_manifest['metadata']['namespace'] if 'namespace' in release_manifest['metadata'] else None)
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

def print_default_config():
    """打印默认配置文件，类似 helm show values，可以使用重定向另行保存
    """
    with open(os.path.join(BASEDIR, DEFAULT_CONFIG_FILE), 'r', encoding='utf-8') as config_file:
        print(config_file.read())

if __name__ == '__main__':
    
    with open(os.path.join(BASEDIR, DOC_FILE), 'r') as doc_file:
        doc_content = doc_file.read()
    parser = argparse.ArgumentParser(description=doc_content, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('action', type=str, help='执行的操作，目前支持的操作：generate-comparison-file、show-default-config')
    parser.add_argument('release_name', nargs='?', type=str, help='Release Name')
    parser.add_argument('chart', nargs='?', type=str, help='Chart local path or package')
    parser.add_argument('--values', type=str, help='自定义 values 文件路径')
    parser.add_argument('--output-path', type=str, default=os.path.join(CURRENT_DIRECTORY, DEFAULT_OUPUT_DIRNAME), help='输出比对文件的目录')
    parser.add_argument('--config-path', type=str, default=os.path.join(BASEDIR, DEFAULT_CONFIG_FILE), help='自定义脚本配置文件路径')
    parser.add_argument('--dry-run', nargs='?', const=True, type=bool, help='仅模拟运行，不实际变更集群，update_ownership 操作可使用')
    args = parser.parse_args()
    
    if args.action == 'show-default-config':
        print_default_config()
    elif args.action == 'generate-comparison-file':
        diff(chart_path=args.chart,
            release_name=args.release_name,
            values=args.values,
            output_path=args.output_path,
            config_path=args.config_path)
    else:
        print('Not supported action!')
