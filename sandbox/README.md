# Execution Sandbox Architecture

This directory defines container-based isolation policies, execution runtimes, and security enforcement mechanisms for evaluating untrusted generated code.

## Security Principles

1. **Strict Non-Privileged Execution**: Generated code is never executed directly inside the host FastAPI process.
2. **Network Isolation**: By default, code execution containers run with `--network none`.
3. **Resource Capping**: Hard memory limits (e.g. 512MB), CPU caps (e.g. 1 core), and bounded execution timeouts (e.g. 10s) prevent denial of service and infinite loops.
4. **Read-Only Root Filesystem**: Write permissions are restricted to transient ephemeral `/tmp` workspaces that are purged immediately after execution.
5. **No Host Directory Mounting**: Sensitive host paths (`~/.ssh`, source code repositories, environment secrets) are never mounted into sandbox containers.
