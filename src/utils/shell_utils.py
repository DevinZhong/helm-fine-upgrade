#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import subprocess


def run_cmd(cmd_args, input=None) -> str:
    if os.environ.get('HELM_DEBUG', '0') == '1':
        print(f'执行命令：{cmd_args}')
    return_cmd = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding='utf-8', input=input, text=True)
    if return_cmd.returncode == 0:
        return return_cmd.stdout
    else:
        print(f'命令执行失败: {cmd_args}')
        print(return_cmd.stderr)
        return None
