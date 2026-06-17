#!/usr/bin/env python
#-*- coding:utf-8 -*-

import time
import yaml
from typing import List
from utils.shell_utils import run_cmd

def apply_manifests(rendered_manifests: List[dict]) -> None:
    """execute `kubectl apply -f` for the rendered manifests.

    Args:
        rendered_manifests (List[dict]): rendered manifests which will apply
    """
    apply_cmd = ['kubectl', 'apply', '-f', '-']
    print(run_cmd(apply_cmd, input=yaml.dump_all(rendered_manifests, allow_unicode=True)))

def apply_deployment(manifest):
    name = manifest['metadata']['name']
    namespace = manifest['metadata']['namespace'] if 'namespace' in manifest['metadata'] else None

    apply_cmd = ['kubectl', 'apply', '-f', '-']
    print(run_cmd(apply_cmd, input=yaml.dump(manifest, allow_unicode=True)))

    try_times = 0
    while try_times < 20:
        if is_deployment_ready(name, namespace):
            return
        try_times += 1
        time.sleep(5)
    raise Exception(f'{namespace}:{name} 部署失败！')

def is_deployment_ready(name, namespace=None) -> bool:
    check_cmd = ['kubectl', 'get', 'Deployment', name, '-o', 'yaml']
    if namespace is not None:
        check_cmd.extend(['-n', namespace])
    output = run_cmd(check_cmd)
    if output is None:
        return False
    deployment = yaml.safe_load(output)
    desired = deployment.get('spec', {}).get('replicas', 1)
    status = deployment.get('status', {})
    return status.get('readyReplicas', 0) >= desired \
        and status.get('updatedReplicas', 0) >= desired \
        and status.get('availableReplicas', 0) >= desired

def delete_deployment(namespace, name):
    delete_cmd = ['kubectl', 'delete', 'Deployment', name]
    if namespace is not None:
        delete_cmd.extend(['-n', namespace])
    print(run_cmd(delete_cmd))
