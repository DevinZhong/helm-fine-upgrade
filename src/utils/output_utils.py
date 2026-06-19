#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json
import sys
import yaml

SUPPORTED_OUTPUT_FORMATS = ('yaml', 'json')
FAILURE_EXIT_CODE = 2

def print_structured_output(data, output_format='yaml') -> None:
    if output_format == 'json':
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_format == 'yaml':
        print(yaml.dump(data, allow_unicode=True, sort_keys=False))
    else:
        raise ValueError(f'Unsupported output format: {output_format}')

def print_status(message: str) -> None:
    print(message, file=sys.stderr)

def parse_fail_on(fail_on: str) -> set:
    if not fail_on:
        return set()
    return {
        item.strip()
        for item in fail_on.split(',')
        if item.strip()
    }

def get_triggered_failures(data: dict, fail_on: str) -> dict:
    fail_on_fields = parse_fail_on(fail_on)
    summary = data.get('summary', {}) if isinstance(data, dict) else {}
    return {
        field: summary.get(field)
        for field in sorted(fail_on_fields)
        if summary.get(field, 0)
    }

def exit_if_fail_on_triggered(data: dict, fail_on: str) -> None:
    triggered = get_triggered_failures(data, fail_on)
    if not triggered:
        return
    details = ', '.join(
        f'{field}={value}' for field, value in triggered.items())
    print_status(f'Fail-on condition triggered: {details}')
    raise SystemExit(FAILURE_EXIT_CODE)
