from http import HTTPMethod, HTTPStatus
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, JsonValue, PositiveFloat, RootModel, model_validator
from pydantic.networks import HttpUrl

from pytest_http_engine.models.types import (
    FunctionImportName,
    JMESPathExpression,
    JSONSchemaInline,
    PartialTemplateStr,
    RegexPattern,
    SerializablePath,
    TemplateExpression,
    VariableName,
    XMLSting,
)


class SSLConfig(BaseModel):
    verify: Literal[True, False] | SerializablePath | TemplateExpression = Field(
        default=True,
        description="SSL certificate verification. True (verify), False (no verification), or path to CA bundle.",
        examples=[False, "/path/to/ca-bundle.crt", "{{ verify_ssl }}"],
    )
    cert: tuple[SerializablePath | PartialTemplateStr, SerializablePath | PartialTemplateStr] | SerializablePath | PartialTemplateStr | None = Field(
        default=None,
        description="SSL client certificate. Single file path or tuple of (cert_path, key_path).",
        examples=[
            ["/path/to/client.crt", "/path/to/client.key"],
            ["/path/to/{{ client_cert_name }}", "/path/to/client.key"],
            "/path/to/client.pem",
            "/path/to/{{ cert_file_name }}",
        ],
    )


class UserFunctionName(RootModel):
    root: FunctionImportName | PartialTemplateStr = Field(
        description="Name of the function to be called.",
        examples=[
            "module.submodule:funcname",
            "module.{{ submodule_name }}:funcname",
        ],
    )


class UserFunctionKwargs(BaseModel):
    function: UserFunctionName
    kwargs: dict[VariableName, Any] = Field(default_factory=dict, description="Function arguments.")


UserFunctionCall = UserFunctionName | UserFunctionKwargs


class Functions(RootModel):
    root: list[UserFunctionCall] = Field(default_factory=list)

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]


class JsonBody(BaseModel):
    """JSON request body."""

    json: JsonValue = Field(description="JSON data to send.")


class XmlBody(BaseModel):
    """XML request body."""

    xml: XMLSting | PartialTemplateStr = Field(description="XML content as string.")


class FormBody(BaseModel):
    """Form-encoded request body."""

    form: dict[str, Any] = Field(description="Form data to be URL-encoded.")


class RawBody(BaseModel):
    """Raw text request body."""

    raw: str = Field(description="Raw text content.")


class FilesBody(BaseModel):
    """Multipart file upload request body."""

    files: dict[str, SerializablePath | PartialTemplateStr] = Field(description="Files to upload from file paths.")


# Union type for all possible body types
RequestBody = JsonBody | XmlBody | FormBody | RawBody | FilesBody


class CallSecurity(BaseModel):
    ssl: SSLConfig = Field(
        default_factory=SSLConfig,
        description="SSL/TLS configuration.",
    )
    auth: UserFunctionCall | None = Field(
        default=None,
        description="User function to create custom authentication.",
    )


class Request(CallSecurity):
    url: HttpUrl | PartialTemplateStr = Field()
    method: HTTPMethod | TemplateExpression = Field(default=HTTPMethod.GET)
    params: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: RequestBody | None = Field(default=None, description="Request body configuration.")
    timeout: PositiveFloat | TemplateExpression = Field(default=30.0, description="Request timeout in seconds.")
    allow_redirects: Literal[True, False] | TemplateExpression = Field(default=True, description="Whether to follow redirects.")


class Save(BaseModel):
    vars: dict[str, JMESPathExpression | PartialTemplateStr] = Field(default_factory=dict, description="Dictionary of JMESPath expressions to extract the value from the response.")
    functions: Functions = Field(default_factory=Functions, description="List of functions to be called to save data from HTTP response.")


class ResponseBody(BaseModel):
    schema: JSONSchemaInline | SerializablePath | PartialTemplateStr | None = Field(default=None, description="JSON schema or path to schema file to validate the whole body with.")
    contains: list[str] = Field(default_factory=list, description="Substrings that must be present in the response body.")
    not_contains: list[str] = Field(default_factory=list, description="Substrings that must NOT be present in the response body.")
    matches: list[RegexPattern] = Field(default_factory=list, description="Regular expressions the response body must match.")
    not_matches: list[RegexPattern] = Field(default_factory=list, description="Regular expressions the response body must NOT match.")


class Verify(BaseModel):
    status: HTTPStatus | None | TemplateExpression = Field(default=None, description="Expected HTTP status code.")
    headers: dict[str, str] = Field(default_factory=dict, description="Expected response headers (case-insensitive).")
    vars: dict[str, Any] = Field(default_factory=dict, description="Expected values for variables from data context.")
    functions: Functions = Field(default_factory=Functions, description="List of functions to be called to verify the response and data context.")
    body: ResponseBody = Field(default_factory=ResponseBody, description="Direct response body validation.")


class Decorated(BaseModel):
    marks: list[str] = Field(default_factory=list, description="List of pytest markers to be applied.", examples=["xfail", "skip"])
    fixtures: list[str] = Field(default_factory=list, description="List of pytest fixture names to be requested.")
    vars: dict[str, Any] = Field(default_factory=dict, description="Variables to inject into data context. Useful for common references.")

    @model_validator(mode="after")
    def validate_variable_naming_conflicts(self) -> Self:
        """Validate that fixtures don't conflict with vars."""
        conflicting_vars = set(set(self.fixtures) & self.vars.keys())
        if len(conflicting_vars) > 0:
            var_names = ",".join(conflicting_vars)
            raise ValueError(f"Conflicting fixtures and vars: {var_names}")

        return self


class Stage(Decorated):
    name: str = Field(description="Stage name. Human readable, no need to be unique.")
    always_run: Literal[True, False] | TemplateExpression = Field(
        default=False,
        description="Run this stage even if previous stages failed. Must be a boolean or a complete template expression that evaluates to a boolean.",
        examples=[
            True,
            False,
            "{{ should_run }}",
            "{{ env == 'production' }}",
            "{{ not skip_stage }}",
        ],
    )
    request: Any = Field(description="HTTP request details.")
    save: Any = Field(default_factory=Save, description="Configuration for saving data from HTTP response.")
    verify: Any = Field(default_factory=Verify, description="Configuration for verifications (asserts) on available data.")


class Scenario(Decorated, CallSecurity):
    stages: list[Stage] = Field(default_factory=list, description="Stages collection.")
