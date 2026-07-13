# Security Policy

## Supported Versions

Security fixes are made for the latest released version of `helm-fine-upgrade`.
Please update to the latest release before reporting an issue when possible.

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Earlier releases | No |

## Reporting a Vulnerability

Do not open a public GitHub issue for a suspected vulnerability. Send a concise
report to devinzhong@outlook.com with the affected version or commit,
reproduction steps or a proof of concept, and potential impact. Do not include
credentials, kubeconfig files, access tokens, or sensitive cluster data.

The maintainer will acknowledge the report, assess it, and coordinate a fix or
disclosure when appropriate.

## Scope

Reports are especially useful for command execution, plugin installation and
release packaging, unsafe handling of Kubernetes resource metadata, and
accidental disclosure of sensitive information in command output.
