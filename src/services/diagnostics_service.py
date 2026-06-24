#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from utils.output_utils import print_structured_output

ROOT_DIR = Path(__file__).resolve().parents[2]


def _detect_plugin_dir() -> Path:
    plugin_dir = os.environ.get('HELM_PLUGIN_DIR')
    if plugin_dir:
        return Path(plugin_dir).resolve()
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parents[1]
    return ROOT_DIR



def _read_plugin_version(plugin_dir: Path) -> str:
    plugin_yaml_path = plugin_dir / 'plugin.yaml'
    if not plugin_yaml_path.is_file():
        return None
    for line in plugin_yaml_path.read_text(encoding='utf-8').splitlines():
        if line.startswith('version:'):
            return line.split(':', 1)[1].strip().strip("'").strip('"')
    return None

def _run_command(command: list) -> tuple:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8',
        text=True,
    )
    return result.returncode, (result.stdout or '').strip(), (result.stderr or '').strip()


def _get_helm_version() -> dict:
    path = shutil.which('helm')
    if not path:
        return {
            'available': False,
            'path': None,
            'version': None,
            'error': 'helm not found in PATH',
        }
    returncode, stdout, stderr = _run_command(['helm', 'version', '--short'])
    return {
        'available': returncode == 0,
        'path': path,
        'version': stdout if returncode == 0 else None,
        'error': None if returncode == 0 else (stderr or stdout or 'helm version failed'),
    }


def _get_kubectl_version() -> dict:
    path = shutil.which('kubectl')
    if not path:
        return {
            'available': False,
            'path': None,
            'version': None,
            'error': 'kubectl not found in PATH',
        }
    command_variants = [
        ['kubectl', 'version', '--client=true', '--output=yaml'],
        ['kubectl', 'version', '--client', '--short'],
    ]
    last_error = None
    for command in command_variants:
        returncode, stdout, stderr = _run_command(command)
        if returncode == 0:
            version = stdout.splitlines()[0] if stdout else ''
            if 'gitVersion:' in stdout:
                for line in stdout.splitlines():
                    if line.strip().startswith('gitVersion:'):
                        version = line.split(':', 1)[1].strip().strip('"')
                        break
            return {
                'available': True,
                'path': path,
                'version': version,
                'error': None,
            }
        last_error = stderr or stdout or 'kubectl version failed'
    return {
        'available': False,
        'path': path,
        'version': None,
        'error': last_error,
    }


def build_doctor_report() -> dict:
    plugin_dir = _detect_plugin_dir()
    binary_name = 'fine-upgrade.exe' if os.name == 'nt' else 'fine-upgrade'
    binary_path = plugin_dir / 'bin' / binary_name
    source_path = plugin_dir / 'src' / 'main.py'
    readme_path = plugin_dir / 'README.md'
    config_path = plugin_dir / 'config.yml'
    mode = 'binary' if getattr(sys, 'frozen', False) else 'source'

    return {
        'plugin': {
            'version': _read_plugin_version(plugin_dir) or os.environ.get('HELM_PLUGIN_VERSION') or 'unknown',
            'mode': mode,
            'plugin_dir': str(plugin_dir),
            'entrypoint': sys.executable if getattr(sys, 'frozen', False) else str(source_path),
        },
        'platform': {
            'os': platform.system().lower(),
            'arch': platform.machine().lower(),
            'python_version': platform.python_version(),
            'frozen': getattr(sys, 'frozen', False),
        },
        'dependencies': {
            'helm': _get_helm_version(),
            'kubectl': _get_kubectl_version(),
        },
        'installation': {
            'binary_exists': binary_path.is_file(),
            'binary_path': str(binary_path),
            'source_exists': source_path.is_file(),
            'source_path': str(source_path),
            'readme_exists': readme_path.is_file(),
            'default_config_exists': config_path.is_file(),
        },
        'environment': {
            'helm_plugin_dir_env': os.environ.get('HELM_PLUGIN_DIR'),
            'helm_namespace': os.environ.get('HELM_NAMESPACE') or os.environ.get('NAMESPACE') or 'default',
            'kubeconfig': os.environ.get('FINE_UPGRADE_KUBECONFIG'),
            'kube_context': os.environ.get('FINE_UPGRADE_KUBE_CONTEXT'),
            'timeout': os.environ.get('FINE_UPGRADE_TIMEOUT'),
        },
    }


def doctor(output_format: str = 'yaml') -> None:
    print_structured_output(build_doctor_report(), output_format)