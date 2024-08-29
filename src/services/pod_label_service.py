#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import yaml
from multiprocessing import Pool
from utils.shell_utils import run_shell_cmd
from utils.helm_utils import get_api_object_spec
from utils.helm_utils import get_api_object_spec, get_all_release_api_objects, manifests_list_to_dict, get_manifest_unique_key
from utils.kube_ops_utils import apply_deployment, delete_deployment

APPLY_CMD = 'kubectl apply -f -'

def rolling_update_pod_labels(chart_path, release_name, values, dry_run):
    """
    滚动更新 Pod 的标签，服务不中断
    """
    shell_cmd = f'helm template --is-upgrade --no-hooks --skip-crds {release_name} {chart_path}'
    if values is not None:
        shell_cmd += f' -f {values}'
    print('执行 helm template 命令...')
    cmd_output = run_shell_cmd(shell_cmd)
    template = yaml.safe_load_all(cmd_output)

    deployments = []
    service_map = {}
    for rendered_manifest in template:
        kind = rendered_manifest['kind']
        if kind == 'Deployment':
            deployments.append(rendered_manifest)
        elif kind == 'Service':
            if 'selector' not in rendered_manifest['spec']:
                # 非业务服务的情况，仅指定 Endpoint 的场景，跳过
                continue
            namespace = rendered_manifest['metadata']['namespace'] if 'namespace' in rendered_manifest['metadata'] else None
            if 'name' not in rendered_manifest['spec']['selector']:
                continue
            deployment_name = rendered_manifest['spec']['selector']['name']
            service_map[f'{namespace}:{deployment_name}'] = rendered_manifest

    cluster_original_manifests = get_all_release_api_objects(release_name)
    cluster_manifest_dict = manifests_list_to_dict(cluster_original_manifests)

    # 最多同时对5个 Deployment 进行滚动更新
    pool = Pool(processes=5)
    results = []
    print('开始逐一检查Deployment对象的Pod标签配置...')
    for rendered_deployment_manifest in deployments:
        name = rendered_deployment_manifest['metadata']['name']
        namespace = rendered_deployment_manifest['metadata']['namespace'] if 'namespace' in rendered_deployment_manifest['metadata'] else None
        manifest_unique_key = get_manifest_unique_key(rendered_deployment_manifest)
        if manifest_unique_key in cluster_manifest_dict:
            cluster_manifest = cluster_manifest_dict[manifest_unique_key]
        else:
            cluster_manifest = get_api_object_spec('Deployment', name, namespace=namespace)
        if cluster_manifest is None:
            continue

        itemMatchLabels = rendered_deployment_manifest['spec']['selector']['matchLabels']
        specMatchLabels = cluster_manifest['spec']['selector']['matchLabels']
        if yaml.dump(itemMatchLabels, allow_unicode=True) == yaml.dump(specMatchLabels, allow_unicode=True):
            continue
        if dry_run:
            print(f'{namespace}:{name} 需对Pod进行滚动更新.')
            continue
        # 异步处理滚动更新逻辑
        result = pool.apply_async(rolling_update_worker, args=(rendered_deployment_manifest, cluster_manifest, service_map, APPLY_CMD))
        results.append(result)

    # 获取异步结果
    for result in results:
        try:
            print(result.get())
        except Exception as e:
            print(e)

def rolling_update_worker(rendered_deployment_manifest, cluster_deployment_manifest, service_map, apply_cmd):
    name = rendered_deployment_manifest['metadata']['name']
    namespace = rendered_deployment_manifest['metadata']['namespace'] if 'namespace' in rendered_deployment_manifest['metadata'] else None
    itemMatchLabels = rendered_deployment_manifest['spec']['selector']['matchLabels']
    specMatchLabels = cluster_deployment_manifest['spec']['selector']['matchLabels']
    specTemplateLables = cluster_deployment_manifest['spec']['template']['metadata']['labels']

    # 1. 创建临时 Deployment 以保持服务不中断
    specMatchLabels['rolling-update-pod-labels-flag'] = '1'
    specTemplateLables['rolling-update-pod-labels-flag'] = '1'
    temp_name = f'{name}-rolling-temp'
    cluster_deployment_manifest['metadata']['name'] = temp_name
    apply_deployment(cluster_deployment_manifest)
    # 2. 临时 Deployment 就绪后删除旧 Deployment
    delete_deployment(namespace, name)
    # 3. 使用新 Pod 标签创建 Deployment
    cluster_deployment_manifest['metadata']['name'] = name
    cluster_deployment_manifest['spec']['selector']['matchLabels'] = itemMatchLabels
    cluster_deployment_manifest['spec']['template']['metadata']['labels'] = itemMatchLabels
    apply_deployment(cluster_deployment_manifest)
    # 4. 新 Deployment 就绪后更新 Service，把流量切回去
    serviceItem = service_map[f'{namespace}:{name}']
    print(run_shell_cmd(apply_cmd, input=yaml.dump(serviceItem, allow_unicode=True)))
    # 5. 流量切回去后，将临时 Deployment 删除
    delete_deployment(namespace, temp_name)

    return f'{namespace}:{name} 滚动更新完成！'
