#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import os
import argparse
from utils.yaml_utils import init_yaml_representer
from utils.helm_utils import configure_kube_options
from utils.output_utils import SUPPORTED_OUTPUT_FORMATS

if getattr(sys, 'frozen', False):
    BASEDIR = sys._MEIPASS
else:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_DIRECTORY = os.getcwd()

init_yaml_representer()

DOC_FILE = 'README.md' if getattr(sys, 'frozen', False) else '../README.md'
DEFAULT_CONFIG_FILE = 'config.yml' if getattr(sys, 'frozen', False) else './config.yml'
DEFAULT_OUPUT_DIRNAME = 'helm-fine-upgrade'

def print_default_config():
    """打印默认配置文件，类似 helm show values，可以使用重定向另行保存"""
    with open(os.path.join(BASEDIR, DEFAULT_CONFIG_FILE), 'r', encoding='utf-8') as config_file:
        print(config_file.read())

def add_common_options(parser):
    parser.add_argument('--namespace', type=str, help='Release namespace')
    parser.add_argument('--kubeconfig', type=str, help='Kubeconfig file path')
    parser.add_argument('--context', '--kube-context', dest='context',
                        type=str, help='Kubernetes context')
    parser.add_argument('--timeout', type=str, help='Kubectl request timeout, for example 30s')
    parser.add_argument('--values', type=str, help='自定义 values 文件路径')
    parser.add_argument('--output', type=str,
                        default=os.path.join(CURRENT_DIRECTORY, DEFAULT_OUPUT_DIRNAME),
                        help='输出比对文件的目录')
    parser.add_argument('--config', type=str,
                        default=os.path.join(BASEDIR, DEFAULT_CONFIG_FILE),
                        help='自定义脚本配置文件路径')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅模拟运行，不实际变更集群')
    parser.add_argument('--debug', action='store_true',
                        help='打印执行的 Helm/kubectl 命令')
    parser.add_argument('--output-format', choices=SUPPORTED_OUTPUT_FORMATS,
                        default='yaml', help='结构化输出格式')
    parser.add_argument('-l', '--selector', default='', type=str,
                        help='标签选择器，用于过滤 Deployment，控制影响范围')

def add_release_chart_args(parser, chart_required=True):
    parser.add_argument('release_name', type=str, help='Release Name')
    if chart_required:
        parser.add_argument('chart', type=str, help='Chart local path or package')
    else:
        parser.add_argument('chart', nargs='?', type=str,
                            help='Chart local path or package')

def build_parser():
    with open(os.path.join(BASEDIR, DOC_FILE), 'r', encoding='utf-8') as doc_file:
        doc_content = doc_file.read()
    parser = argparse.ArgumentParser(
        description=doc_content,
        formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest='action', required=True)

    subparsers.add_parser('show-default-config', help='打印默认插件配置')

    state_check_parser = subparsers.add_parser(
        'state-check',
        help='检查 Helm release 记录、集群运行态和当前 chart 之间的一致性')
    add_common_options(state_check_parser)
    add_release_chart_args(state_check_parser, chart_required=False)

    adopt_plan_parser = subparsers.add_parser(
        'adopt-plan',
        help='分析 chart 渲染资源和集群已有资源的接管关系')
    add_common_options(adopt_plan_parser)
    add_release_chart_args(adopt_plan_parser)

    plan_parser = subparsers.add_parser(
        'plan',
        help='生成升级计划')
    add_common_options(plan_parser)
    add_release_chart_args(plan_parser)

    apply_parser = subparsers.add_parser(
        'apply',
        help='根据 chart 渲染结果应用资源')
    add_common_options(apply_parser)
    add_release_chart_args(apply_parser)

    comparison_parser = subparsers.add_parser(
        'generate-comparison-file',
        help='生成集群当前配置与 chart 配置的对比文件')
    add_common_options(comparison_parser)
    add_release_chart_args(comparison_parser)

    image_parser = subparsers.add_parser(
        'update-values-image-version',
        help='更新 values.yaml 的镜像版本')
    add_common_options(image_parser)
    add_release_chart_args(image_parser)

    metadata_parser = subparsers.add_parser(
        'update-ownership-metadata',
        help='更新 API 对象的 Helm 元数据信息')
    add_common_options(metadata_parser)
    add_release_chart_args(metadata_parser)

    labels_parser = subparsers.add_parser(
        'rolling-update-pod-labels',
        help='滚动更新 Pod 标签')
    add_common_options(labels_parser)
    add_release_chart_args(labels_parser)

    return parser

def configure_runtime_options(args):
    configure_kube_options(
        namespace=getattr(args, 'namespace', None),
        kubeconfig=getattr(args, 'kubeconfig', None),
        context=getattr(args, 'context', None),
        timeout=getattr(args, 'timeout', None))
    os.environ['DRY_RUN_FLAG'] = '1' if getattr(args, 'dry_run', False) else '0'
    if getattr(args, 'debug', False):
        os.environ['HELM_DEBUG'] = '1'

def dispatch(args):
    configure_runtime_options(args)
    if args.action == 'show-default-config':
        print_default_config()
    elif args.action == 'state-check':
        from services.helm_service import state_check
        state_check(release_name=args.release_name,
             chart_path=args.chart,
             values=args.values,
             config_path=args.config,
             output_format=args.output_format)
    elif args.action == 'adopt-plan':
        from services.metadata_service import adopt_plan
        adopt_plan(chart_path=args.chart,
             release_name=args.release_name,
             values=args.values,
             selector=args.selector,
             output_format=args.output_format)
    elif args.action == 'plan':
        from services.helm_service import plan_upgrade
        plan_upgrade(chart_path=args.chart,
             release_name=args.release_name,
             values=args.values,
             config_path=args.config,
             selector=args.selector,
             output_format=args.output_format)
    elif args.action == 'apply':
        from services.helm_service import apply_upgrade
        apply_upgrade(chart_path=args.chart,
             release_name=args.release_name,
             values=args.values,
             selector=args.selector)
    elif args.action == 'generate-comparison-file':
        from services.helm_service import diff
        diff(chart_path=args.chart,
             release_name=args.release_name,
             values=args.values,
             output_path=args.output,
             config_path=args.config,
             selector=args.selector)
    elif args.action == 'update-values-image-version':
        from services.image_service import image_version_diff
        image_version_diff(chart_path=args.chart,
                           release_name=args.release_name,
                           values=args.values,
                           config_path=args.config,
                           dry_run=args.dry_run,
                           output_format=args.output_format)
    elif args.action == 'update-ownership-metadata':
        from services.metadata_service import set_ownership_metadata
        set_ownership_metadata(chart_path=args.chart,
                               release_name=args.release_name,
                               values=args.values,
                               selector=args.selector,
                               dry_run=args.dry_run)
    elif args.action == 'rolling-update-pod-labels':
        from services.pod_label_service import rolling_update_pod_labels
        rolling_update_pod_labels(chart_path=args.chart,
                               release_name=args.release_name,
                               values=args.values,
                               selector=args.selector,
                               dry_run=args.dry_run)

if __name__ == '__main__':
    dispatch(build_parser().parse_args())
