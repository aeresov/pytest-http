[![image](https://img.shields.io/pypi/v/pytest-http)](https://pypi.python.org/pypi/pytest-http)
[![image](https://img.shields.io/pypi/l/pytest-http)](https://github.com/aeresov/pytest-http/blob/main/LICENSE)
[![image](https://img.shields.io/pypi/pyversions/pytest-http)](https://pypi.python.org/pypi/pytest-http)

# pytest-http

A pytest plugin for testing HTTP endpoints.

## Overview

`pytest-http` is an integration testing framework for HTTP APIs based on battle-hardened [requests](https://requests.readthedocs.io) lib.\
It aims at helping with common HTTP API testing scenarios, where user needs to make several calls in specific order using data obtained along the way, like auth tokens or resource ids.

## Installation

Install normally via package manager of your choice from PyPi:

```bash
pip install pytest-http
```

or directly from Github, in case you need a particular ref:

```bash
pip install 'git+https://github.com/aeresov/pytest-http@main'
```

### Optional dependencies

The following optional dependencies are available:

-   `mcp`: installs MCP server package and its starting script. Details in [MCP Server](#mcp-server).

## Features

### Pytest integration

Most of pytest magic can be used: markers, fixtures, other plugins.\
> NOTE: parametrization is not yet implemented, therefore `parametrize` marker won't have any effect.

### Declarative format

Test scenarios are written declaratively in JSON files.\
`pytest-http` supports JSONRef, so use can reuse arbitrary parts of your scenarios with `$ref` directive.\
Properties are merged in a greedy way with type checking.

### Multi-stage tests

Each test scenario contains 1+ stages; each stage is a single HTTP call.\
`pytest-http` executes stages in the order they are listed in scenario file; one stage failure stops the execution chain.

### Common data context and variable substitution

`pytest-http` maintains key-value data storage throughout the execution.\
This storage ("common data context") is populated with declared variables, fixtures and data saved by stages. The data remains there throughout the scenario execution.\
Writing scenarios, you can use Jinja-style expressions like `"{{ var }}"` for JSON values. `pytest-http` does variable substitution dynamically right before executing a stage, and uses common data context keys as variables in these expressions.\
Values from common data context also might be verified during verified/asserted.

### User functions

`pytest-http` can import and call regular python functions:
- to extract data from HTTP response
- to verify HTTP response and values in common data context
- to provide [custom authentication for requests](https://requests.readthedocs.io/en/latest/user/advanced/#custom-authentication)

### JMESPath support

`pytest-http` can extract values from JSON responses using JMESPath expressions directly.

### JSON schema support

`pytest-http` can verify JSON reponses against user-defined JSON schema.

## Quick Start

Create a JSON test file named like `test_<name>.<suffix>.json` (default suffix is `http`):

```python
# conftest.py
import pytest
from datetime import datetime

@pytest.fixture
def now_utc():
    return datetime.now()
```

```json
{
    "vars": {
        "user_id": 1
    },
    "stages": [
        {
            "name": "get_user",
            "request": {
                "url": "https://api.example.com/users/{{ user_id }}"
            },
            "save": {
                "vars": {
                    "user_name": "user.name"
                }
            },
            "verify": {
                "status": 200
            }
        },
        {
            "name": "update_user",
            "fixtures": ["now_utc"],
            "request": {
                "url": "https://api.example.com/users/{{ user_id }}",
                "method": "PUT",
                "body": {
                    "json": {
                        "user": {
                            "name": "{{ user_name }}_updated",
                            "timestamp": "{{ str(now_utc) }}"
                        }
                    }
                }
            },
            "verify": {
                "status": 200
            }
        },
        {
            "name": "cleanup",
            "always_run": true,
            "request": {
                "url": "https://api.example.com/cleanup",
                "method": "POST"
            }
        }
    ]
}
```

Scenario we created:
- common data context is seeded with the first variable `user_id`
- **get_user**\
url is assembled using `user_id` variable from common data context\
HTTP GET call is made\
we verify the call returned code 200\
assuming JSON body is returned, we extract a value by JMESPath expression `user.name` and save it to common data context under `user_name` key
- **update_user**\
`now_utc` fixture value is injected into common data context\
url is assembled using `user_id` variable from common data context\
we create JSON body in place using values from common data context, note that `now_utc` is converted to string in place\
HTTP PUT call with body is made\
we verify the call returned code 200\
- **cleanup**\
finalizing call meant for graceful exit\
`always_run` parameter means this stage will be executed regardless of errors in previous stages

For detailed examples see [USAGE.md](USAGE.md).

## Configuration

- Test file discovery is based on this name pattern: `test_<name>.<suffix>.json`.  
The suffix is configurable as pytest ini option, default value is **http**.

## MCP Server

`pytest-http` includes an MCP (Model Context Protocol) server to aid AI code assistants.

### Installation

The optional dependency `mcp` installs MCP server's package and `pytest-http-mcp` script.\
Use this script as call target for your MCP configuration.

```json
// .mcp.json for Claude Code
{
    "mcpServers": {
        "pytest-http": {
            "type": "stdio",
            "command": "uv",
            "args": ["run", "pytest-http-mcp"],
            "env": {}
        }
    }
}
```

### Features

The MCP server provides:

-   **Scenario validation** - validate test scenario and scan for possible problems

## Documentation

- [Usage Examples](USAGE.md) - Practical code examples
- [Full Documentation](https://aeresov.github.io/pytest-http) - Complete guide
- [Changelog](CHANGELOG.md) - Release notes

## Thanks

`pytest-http` was heavily inspired by [Tavern](https://github.com/taverntesting/tavern) and [pytest-play](https://github.com/davidemoro/pytest-play).  
Crucial parts rely on [requests](https://requests.readthedocs.io), [pytest-order](https://github.com/pytest-dev/pytest-order) and [Pydantic](https://docs.pydantic.dev).
