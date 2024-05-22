#!/usr/bin/env python
#-*- coding:utf-8 -*-

from typing import Any

def remove_ignore_fields(obj, ignore_config):
    """
    移除不需要参与比对的字段
    obj: 当前处理对象
    ignore_config: 当前对象需要移除的字段树。_fields 字段内容为当前对象下需要移除的直接字段
    """
    if isinstance(obj, list):
        for item in obj:
            remove_ignore_fields(item, ignore_config)
    else:
        for key in ignore_config:
            if key == '_fields':
                for field in ignore_config[key]:
                    if field in obj:
                        del obj[field]
            elif key in obj:
                if obj[key] is not None:
                    remove_ignore_fields(obj[key], ignore_config[key])
                if not bool(obj[key]):
                    del obj[key]

def set_value(dictionary: dict, keys: str, value: Any):
    """根据 key 序列设置字典值

    Args:
        dictionary (dict): 字典对象
        keys (str): key序列，英文点好分隔
        value (Any): 需要设置的值
    """
    keys = keys.split('.')
    for key in keys[:-1]:  # 循环遍历，但不包括最后一个键
        dictionary = dictionary.setdefault(key, {})
    dictionary[keys[-1]] = value
