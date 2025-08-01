import importlib
import re
from collections.abc import Callable
from typing import Any

import requests
from requests.auth import AuthBase


class BaseUserFunction:
    """Base class for user-defined functions."""

    @staticmethod
    def _parse_given_name(func_name: str) -> tuple[str | None, str]:
        # First try the full 'module:function' format
        full_pattern = r"^(?P<module>[a-zA-Z_][a-zA-Z0-9_.]*):(?P<function>[a-zA-Z_][a-zA-Z0-9_]*)$"
        match = re.match(full_pattern, func_name)
        if match:
            return match.group("module"), match.group("function")

        # Then try just the function name without module
        simple_pattern = r"^(?P<function>[a-zA-Z_][a-zA-Z0-9_]*)$"
        match = re.match(simple_pattern, func_name)
        if match:
            return None, match.group("function")

        raise ValueError(f"'{func_name}' does not match 'module:function' or 'function' syntax with valid identifiers")

    @staticmethod
    def _import_function(module_path: str | None, function_name: str) -> Callable[..., Any]:
        if module_path is None:
            # Try to import from conftest module first
            try:
                conftest = importlib.import_module("conftest")
                if hasattr(conftest, function_name):
                    func = getattr(conftest, function_name)
                    if callable(func):
                        return func
            except ImportError:
                pass

            # If not in conftest, try to find in the current test module's globals
            import inspect

            frame = inspect.currentframe()
            if frame is not None:
                # Walk up the call stack to find the frame that has our function
                while frame is not None:
                    if function_name in frame.f_globals:
                        func = frame.f_globals[function_name]
                        if callable(func):
                            return func
                    frame = frame.f_back

            raise ValueError(f"Function '{function_name}' not found in conftest or local namespace")

        # Original module:function logic
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ValueError(f"Cannot import module '{module_path}': {e}") from e

        if not hasattr(module, function_name):
            raise ValueError(f"Function '{function_name}' not found in module '{module_path}'")

        func = getattr(module, function_name)
        if not callable(func):
            raise ValueError(f"'{function_name}' in module '{module_path}' is not callable")

        return func

    @classmethod
    def validate_name(cls, func_name: str) -> str:
        module_path, function_name = cls._parse_given_name(func_name)
        # Only validate if module path is provided
        # If module_path is None, we'll validate at execution time
        if module_path is not None:
            cls._import_function(module_path, function_name)
        # expect ValueError raised here on any error
        return func_name


class VerificationFunction(BaseUserFunction):
    """User function for response verification."""

    @classmethod
    def call(cls, func_name: str, response: requests.Response) -> Any:
        """Call a verification function with response only.

        Args:
            func_name: Function name in 'module:function' format or just 'function' for local imports
            response: The HTTP response object

        Returns:
            The result of the verification function

        Raises:
            ValueError: If function doesn't exist or call fails
        """
        module_path, function_name = cls._parse_given_name(func_name)
        func = cls._import_function(module_path, function_name)
        return func(response)

    @classmethod
    def call_with_kwargs(cls, func_name: str, response: requests.Response, kwargs: dict[str, Any]) -> Any:
        """Call a verification function with response and keyword arguments.

        Args:
            func_name: Function name in 'module:function' format or just 'function' for local imports
            response: The HTTP response object
            kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the verification function

        Raises:
            ValueError: If function doesn't exist or call fails
        """
        module_path, function_name = cls._parse_given_name(func_name)
        func = cls._import_function(module_path, function_name)
        return func(response, **kwargs)


class AuthFunction(BaseUserFunction):
    """User function for authentication."""

    @classmethod
    def call(cls, func_name: str) -> AuthBase:
        """
        Call an authentication function without arguments.

        Args:
            func_name: Function name in 'module:function' format or just 'function' for local imports

        Returns:
            AuthBase: Authentication instance to be used with requests

        Raises:
            ValueError: If function doesn't exist or doesn't return AuthBase instance
        """
        module_path, function_name = cls._parse_given_name(func_name)
        func = cls._import_function(module_path, function_name)

        try:
            auth_instance = func()
        except Exception as e:
            raise ValueError(f"Error calling authentication function '{func_name}': {e}") from e

        if not isinstance(auth_instance, AuthBase):
            raise ValueError(f"Authentication function '{func_name}' must return a requests.AuthBase instance, got {type(auth_instance)}")

        return auth_instance

    @classmethod
    def call_with_kwargs(cls, func_name: str, kwargs: dict[str, Any]) -> AuthBase:
        """
        Call an authentication function with keyword arguments.

        Args:
            func_name: Function name in 'module:function' format or just 'function' for local imports
            kwargs: Keyword arguments to pass to the function

        Returns:
            AuthBase: Authentication instance to be used with requests

        Raises:
            ValueError: If function doesn't exist or doesn't return AuthBase instance
        """
        module_path, function_name = cls._parse_given_name(func_name)
        func = cls._import_function(module_path, function_name)

        try:
            auth_instance = func(**kwargs)
        except Exception as e:
            raise ValueError(f"Error calling authentication function '{func_name}': {e}") from e

        if not isinstance(auth_instance, AuthBase):
            raise ValueError(f"Authentication function '{func_name}' must return a requests.AuthBase instance, got {type(auth_instance)}")

        return auth_instance
