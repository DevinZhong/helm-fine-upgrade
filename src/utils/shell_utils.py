#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import subprocess


HELM_DEBUG = os.environ.get('HELM_DEBUG', '0')
print(f'HELM_DEBUG: {HELM_DEBUG}')

def run_shell_cmd(shell_cmd, input=None) -> str:
    if HELM_DEBUG:
        print(f'执行命令：{shell_cmd}')
    if input is not None:
        return_cmd = subprocess.run(shell_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True, input=input, text=True)
    else:
        return_cmd = subprocess.run(shell_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True)
    if return_cmd.returncode == 0:
        return return_cmd.stdout
    else:
        print(f'命令执行失败: {shell_cmd}')
        print(return_cmd.stderr)
        return None