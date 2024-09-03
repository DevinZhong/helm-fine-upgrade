#!/usr/bin/env python
#-*- coding:utf-8 -*-

import time
import yaml
from typing import List
from utils.shell_utils import run_shell_cmd

def apply_manifests(rendered_manifests: List[dict]) -> None:
    """execute `kubectl apply -f` for the rendered manifests.

    Args:
        rendered_manifests (List[dict]): rendered manifests which will apply
    """
    apply_cmd = 'kubectl apply -f -'
    print(run_shell_cmd(apply_cmd, input=yaml.dump_all(rendered_manifests, allow_unicode=True)))

def apply_deployment(manifest):
    name = manifest['metadata']['name']
    namespace = manifest['metadata']['namespace'] if 'namespace' in manifest['metadata'] else None
    initialDelaySeconds = manifest['spec']['template']['spec']['containers'][0]['startupProbe']['initialDelaySeconds']

    apply_cmd = 'kubectl apply -f -'
    print(run_shell_cmd(apply_cmd, input=yaml.dump(manifest, allow_unicode=True)))
    time.sleep(initialDelaySeconds)

    check_cmd = f'kubectl get Deployment {name} -n {namespace}'
    check_cmd = check_cmd + " | awk 'NR==2 {print $2}' | awk -F '/' '{print $1 == $2}' | tr -d '[:cntrl:]'"
    try_times = 0
    while try_times < 20:
        if run_shell_cmd(check_cmd) == '1':
            return
        try_times += try_times
        time.sleep(5)
    raise Exception(f'{namespace}:{name} 部署失败！')

def delete_deployment(namespace, name):
    delete_cmd = f'kubectl delete Deployment {name} -n {namespace}'
    print(run_shell_cmd(delete_cmd))
