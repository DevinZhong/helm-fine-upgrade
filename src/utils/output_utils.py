#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json
import sys
import yaml

SUPPORTED_OUTPUT_FORMATS = ('yaml', 'json')

def print_structured_output(data, output_format='yaml') -> None:
    if output_format == 'json':
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_format == 'yaml':
        print(yaml.dump(data, allow_unicode=True, sort_keys=False))
    else:
        raise ValueError(f'Unsupported output format: {output_format}')

def print_status(message: str) -> None:
    print(message, file=sys.stderr)
