#!/usr/bin/env python
#-*- coding:utf-8 -*-

import yaml
from utils.shell_utils import run_shell_cmd

def get_api_object_spec(kind, name, namespace, kubeconfig, debug):
    """
    根据元信息，使用 kubectl 获取API对象的 yaml 配置
    """
    cmd = f'kubectl get {kind} {name} -o yaml'
    if namespace is not None:
        cmd += f' -n {namespace}'
    if kubeconfig is not None:
        cmd += f' --kubeconfig={kubeconfig}'
    cmd_output = run_shell_cmd(cmd, debug)
    if cmd_output is not None:
        return yaml.safe_load(cmd_output if cmd_output is not None else '')
    else:
        return None