from http import HTTPMethod, HTTPStatus
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from pytest_http_engine.types import FunctionName, JMESPathExpression, JSONSchemaInline, JSONSerializable, SerializablePath, VariableName


class SSLConfig(BaseModel):
    """
    SSL/TLS configuration for HTTP requests.

    Attributes:
        verify: Control SSL certificate verification.
                - True: Verify SSL certificates (default)
                - False: Disable verification (security risk, use only for testing)
                - str: Path to custom CA bundle file or directory
        cert: SSL client certificate configuration.
              - str: Path to SSL client certificate file (containing both cert and key)
              - tuple[str, str]: Tuple of (certificate_path, private_key_path)
    """

    verify: bool | SerializablePath | None = Field(default=True, description="SSL certificate verification. True (verify), False (no verification), or path to CA bundle")
    cert: tuple[SerializablePath, SerializablePath] | SerializablePath | None = Field(
        default=None, description="SSL client certificate. Single file path or tuple of (cert_path, key_path)"
    )


class FunctionCall(BaseModel):
    """
    User function call to be made.

    Attributes:
        function: Full qualified name of the function to be called. Function must be available to import.
        kwargs: Dictionary of arguments to be passed to the function.
    """

    function: FunctionName = Field(description="Name of the function to be called.")
    kwargs: dict[VariableName, Any] | None = Field(default=None, description="Function arguments.")


class Functions(RootModel):
    """
    Collection of functions to be called.
    Functions are called in the order they are provided.

    Attributes:
        root:   List of functions provided by user.
                Each item can be a function name or a function call.
                When using a function name, the function is called with the response as the only argument.
                When using a function call, the function is called with the response as the first argument and the kwargs provided.
    """

    root: list[FunctionName | FunctionCall] = Field(default_factory=list)

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]


class Save(BaseModel):
    """
    Configuration on how to save data from the response.
    Data is saved into a dictionary called variable_context. This context is available for all stages in the scenario. Every stage updates the context with its own saves.

    Attributes:
        vars:       A dictionary where key is the variable name and value is the JMESPath expression to extract the value from the response.
                    Dictionary with extracted values is merged into the variable_context.
                    "vars" are processed first.
        functions:  A list of functions to be called to save data.
                    Function returns a dictionary to be merged into the variable_context.
                    Functions are called after "vars".
                    Functions can use variable_context entries for kwargs, including entries from current stage.
    """

    vars: dict[str, JMESPathExpression] | None = Field(default=None, description="Dictionary of JMESPath expressions to extract the value from the response")
    functions: Functions | None = Field(default=None, description="List of functions to be called to save data.")


class ResponseBody(BaseModel):
    """
    Configuration for response body validation.

    Attributes:
        schema:       JSON schema to validate the response body against.
                      Can be either:
                      - An inline JSON schema (dict)
                      - A path to a schema file (str)
        contains:     List of substrings that must be present in the response body.
                      All substrings must be found for verification to pass.
        not_contains: List of substrings that must NOT be present in the response body.
                      If any substring is found, verification fails.
        matches:      List of regular expressions that the response body text must match.
                      All patterns must match for verification to pass.
        not_matches:  List of regular expressions that the response body text must NOT match.
                      If any pattern matches, verification fails.
    """

    schema: JSONSchemaInline | SerializablePath | None = Field(default=None, description="JSON schema or path to schema file")
    contains: list[str] | None = Field(default=None, description="Substrings that must be present in the response body")
    not_contains: list[str] | None = Field(default=None, description="Substrings that must NOT be present in the response body")
    matches: list[str] | None = Field(default=None, description="Regular expressions that must match the response body text")
    not_matches: list[str] | None = Field(default=None, description="Regular expressions that must NOT match the response body text")


class Verify(BaseModel):
    """
    Configuration on how to verify the response.

    Attributes:
        status:    Expected HTTP status code.
        headers:   A dictionary where key is the header name and value is the expected header value.
                   Header names are case-insensitive.
        vars:      A dictionary where key is the variable name and value is the expected value.
                   Variables come from variable_context.
                   Variables from current stage are available.
        functions: List of functions to be called to verify the response.
                   Function returns a boolean value, negative result triggers test failure.
                   Functions are called after "vars".
                   Functions can use variable_context entries for kwargs, including entries from current stage.
        body:      Configuration for response body validation (schema and regex patterns).
    """

    status: HTTPStatus | None = Field(default=None, description="Expected HTTP status code.")
    headers: dict[str, str] | None = Field(default=None, description="Expected response headers (case-insensitive).")
    vars: dict[str, Any] | None = Field(default=None, description="Expected values for variables.")
    functions: Functions | None = Field(default=None, description="List of functions to be called to verify the response.")
    body: ResponseBody | None = Field(default=None, description="Response body validation (schema and regex patterns).")


class JsonBody(BaseModel):
    """JSON request body."""

    json: JSONSerializable = Field(description="JSON data to send")


class XmlBody(BaseModel):
    """XML request body."""

    xml: str = Field(description="XML content as string")


class FormBody(BaseModel):
    """Form-encoded request body."""

    form: dict[str, Any] = Field(description="Form data to be URL-encoded")


class RawBody(BaseModel):
    """Raw text request body."""

    raw: str = Field(description="Raw text content")


class FilesBody(BaseModel):
    """Multipart file upload request body."""

    files: dict[str, SerializablePath] | None = Field(default=None, description="Files to upload from file paths (e.g., '/path/to/file')")


# Union type for all possible body types
RequestBody = JsonBody | XmlBody | FormBody | RawBody | FilesBody


class Request(BaseModel):
    """
    HTTP request configuration.

    Attributes:
        url:      URL to be requested. Can contain variable names for substitution.
        method:   HTTP method to be used.
        params:   Query parameters to be sent.
        headers:  HTTP headers to be sent.
        body:     Request body configuration.
        timeout:  Request timeout in seconds (optional).
        allow_redirects: Whether to follow HTTP redirects (defaults to True).
        ssl:      SSL/TLS configuration for this specific request (overrides scenario SSL settings).
        auth:     Authentication function name for this specific request (overrides scenario auth settings).
    """

    url: str = Field()
    method: HTTPMethod = Field(default=HTTPMethod.GET)
    params: dict[str, Any] | None = Field(default=None)
    headers: dict[str, str] | None = Field(default=None)
    body: RequestBody | None = Field(default=None, description="Request body configuration")
    timeout: float | None = Field(default=30.0, description="Request timeout in seconds", gt=0)
    allow_redirects: bool = Field(default=True, description="Whether to follow redirects")
    ssl: SSLConfig | None = Field(
        default=None,
        description="SSL/TLS configuration for this specific request (overrides scenario SSL settings)",
        examples=[
            {"verify": True},
            {"verify": False},
            {"verify": "/path/to/ca-bundle.crt"},
            {"cert": "/path/to/client.pem"},
            {"cert": ["/path/to/client.crt", "/path/to/client.key"]},
        ],
    )
    auth: FunctionName | FunctionCall | None = Field(default=None, description="Authentication function name or function call (overrides scenario auth settings)")


class Response(BaseModel):
    """
    HTTP response configuration.

    Attributes:
        save:   Configuration on how to save data from the response.
        verify: Configuration on how to verify the response.
    """

    save: Save | None = Field(default=None)
    verify: Verify | None = Field(default=None)


class Stage(BaseModel):
    """
    HTTP request and response configuration.
    Represents a single step in the scenario's test chain.

    Attributes:
        name:     Stage name.
        fixtures: List of pytest fixture names to be supplied to this stage.
        marks:    List of marks to be applied to this stage.
        vars:     Initial variables to seed the variable context for this stage.
        request:  HTTP request configuration.
        response: HTTP response configuration.
        always_run: If True, this stage will run even if previous stages failed (useful for cleanup).
    """

    name: str = Field()
    fixtures: list[str] = Field(default_factory=list, description="List of pytest fixture names for this stage")
    marks: list[str] = Field(default_factory=list, description="List of marks to be applied to this stage", examples=["xfail", "skip"])
    vars: dict[str, Any] | None = Field(default=None, description="Initial variables for the stage context")
    request: Request = Field()
    response: Response | None = Field(default=None)
    always_run: bool = Field(default=False, description="Run this stage even if previous stages failed")

    @model_validator(mode="after")
    def validate_prohibited_marks(self) -> "Stage":
        prohibited_marks = ["skipif", "usefixture", "parametrize"]

        for mark in self.marks:
            for prohibited in prohibited_marks:
                if mark.startswith(f"{prohibited}(") or mark == prohibited:
                    raise ValueError(f"Mark '{prohibited}' is not supported")

        return self

    @model_validator(mode="after")
    def validate_variable_naming_conflicts(self) -> "Stage":
        """Validate that fixtures don't conflict with stage seed vars."""
        if not self.fixtures or not self.vars:
            return self

        fixture_names = set(self.fixtures)
        conflicting_vars = fixture_names & self.vars.keys()

        if conflicting_vars:
            name = next(iter(conflicting_vars))
            raise ValueError(f"Variable name '{name}' conflicts with fixture name in stage '{self.name}'")

        return self


class Scenario(BaseModel):
    """
    Scenario represents a pytest test function that runs a chain of HTTP requests.
    Scenario is organized as a collection of stages that are executed in order.

    Attributes:
        fixtures:   List of pytest fixture names to be supplied with, like a regular pytest function.
        marks:      List of marks to be applied to, like to a regular pytest function.
        vars:       Initial variables to seed the variable context.
        ssl:        SSL/TLS configuration applied to the HTTP session for all requests (optional)
        auth:       Authentication function name applied to the HTTP session for all requests (optional)
        stages:     Collection of stages to execute. Stages with always_run=True will execute even if previous stages failed.
    """

    fixtures: list[str] = Field(default_factory=list, description="List of pytest fixture names")
    marks: list[str] = Field(default_factory=list, description="List of marks to be applied", examples=["xfail", "skip"])
    vars: dict[str, Any] | None = Field(default=None, description="Initial variables for the scenario context")
    ssl: SSLConfig | None = Field(
        default=None,
        description="SSL/TLS configuration applied to the HTTP session for all requests",
        examples=[
            {"verify": True},
            {"verify": False},
            {"verify": "/path/to/ca-bundle.crt"},
            {"cert": "/path/to/client.pem"},
            {"cert": ["/path/to/client.crt", "/path/to/client.key"]},
            {"verify": "/path/to/ca-bundle.crt", "cert": ["/path/to/client.crt", "/path/to/client.key"]},
        ],
    )
    auth: FunctionName | FunctionCall | None = Field(default=None, description="Authentication function name or function call applied to the HTTP session for all requests")
    stages: list[Stage] = Field(default_factory=list, description="Collection of stages to execute")

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def validate_variable_naming_conflicts(self) -> "Scenario":
        """Validate that fixtures don't conflict with initial vars or saved vars."""
        if not self.fixtures:
            return self

        fixture_names = set(self.fixtures)

        # Check for any conflicts with fixtures
        conflicting_vars = set()

        # Check initial vars
        if self.vars:
            conflicting_vars.update(fixture_names & self.vars.keys())

        # Check saved vars
        for stage in self.stages:
            if stage.response and stage.response.save and stage.response.save.vars:
                conflicting_vars.update(fixture_names & stage.response.save.vars.keys())

        if conflicting_vars:
            name = next(iter(conflicting_vars))
            raise ValueError(f"Variable name '{name}' conflicts with fixture name")

        return self

    @model_validator(mode="after")
    def validate_prohibited_marks(self) -> "Scenario":
        prohibited_marks = ["skipif", "usefixture", "parametrize"]

        for mark in self.marks:
            for prohibited in prohibited_marks:
                if mark.startswith(f"{prohibited}(") or mark == prohibited:
                    raise ValueError(f"Mark '{prohibited}' is not supported")

        return self
