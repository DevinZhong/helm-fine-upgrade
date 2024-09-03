#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
import argparse
from utils.yaml_utils import init_yaml_representer
from services.image_service import image_version_diff
from services.helm_service import diff, apply_upgrade
from services.metadata_service import set_ownership_metadata
from services.pod_label_service import rolling_update_pod_labels

if getattr(sys, 'frozen', False):
    BASEDIR = sys._MEIPASS
else:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_DIRECTORY = os.getcwd()

init_yaml_representer()

DOC_FILE = '../README.md'
DEFAULT_CONFIG_FILE = './config.yml'
DEFAULT_OUPUT_DIRNAME = 'helm-fine-upgrade'

def print_default_config():
    """打印默认配置文件，类似 helm show values，可以使用重定向另行保存
    """
    with open(os.path.join(BASEDIR, DEFAULT_CONFIG_FILE), 'r', encoding='utf-8') as config_file:
        print(config_file.read())

if __name__ == '__main__':
    
    with open(os.path.join(BASEDIR, DOC_FILE), 'r') as doc_file:
        doc_content = doc_file.read()
    parser = argparse.ArgumentParser(description=doc_content, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('action', type=str, help='执行的操作，支持的操作类型请查阅 README.md 文档')
    parser.add_argument('release_name', nargs='?', type=str, help='Release Name')
    parser.add_argument('chart', nargs='?', type=str, help='Chart local path or package')
    parser.add_argument('--values', type=str, help='自定义 values 文件路径')
    parser.add_argument('--output', type=str, default=os.path.join(CURRENT_DIRECTORY, DEFAULT_OUPUT_DIRNAME), help='输出比对文件的目录')
    parser.add_argument('--config', type=str, default=os.path.join(BASEDIR, DEFAULT_CONFIG_FILE), help='自定义脚本配置文件路径')
    parser.add_argument('--dry-run', nargs='?', const=True, type=bool, help='仅模拟运行，不实际变更集群，update_ownership 操作可使用')
    parser.add_argument('-l', '--selector', nargs='?', default='', type=str, help='标签选择器，用于过滤 Deployment，控制影响范围')
    args = parser.parse_args()
    
    if args.dry_run:
        os.environ['DRY_RUN_FLAG'] = '1'
    else:
        os.environ['DRY_RUN_FLAG'] = '0'

    if args.action == 'show-default-config':
        print_default_config()
    elif args.action == 'apply':
        apply_upgrade(chart_path=args.chart,
             release_name=args.release_name,
             values=args.values,
             selector=args.selector)
    elif args.action == 'generate-comparison-file':
        diff(chart_path=args.chart,
             release_name=args.release_name,
             values=args.values,
             output_path=args.output,
             config_path=args.config,
             selector=args.selector)
    elif args.action == 'update-values-image-version':
        image_version_diff(chart_path=args.chart,
                           release_name=args.release_name,
                           values=args.values,
                           config_path=args.config,
                           dry_run=args.dry_run)
    elif args.action == 'update-ownership-metadata':
        set_ownership_metadata(chart_path=args.chart,
                               release_name=args.release_name,
                               values=args.values,
                               selector=args.selector,
                               dry_run=args.dry_run)
    elif args.action == 'rolling-update-pod-labels':
        rolling_update_pod_labels(chart_path=args.chart,
                               release_name=args.release_name,
                               values=args.values,
                               selector=args.selector,
                               dry_run=args.dry_run)
    else:
        print('Not supported action!')
