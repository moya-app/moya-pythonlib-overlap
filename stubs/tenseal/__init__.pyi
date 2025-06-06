import typing as t
from enum import Enum
from typing import overload

class SecretKey:
    pass

class BFVVector:
    def __init__(self, context: Context | None = None, vector: list[int | None] | None = None) -> None: ...
    def serialize(self) -> bytes: ...
    @classmethod
    def lazy_load(cls, data: bytes) -> BFVVector: ...
    def copy(self) -> BFVVector: ...
    def decrypt(self, secret_key: SecretKey | None = None) -> list[int]: ...
    def __mul__(self, other: BFVVector) -> BFVVector: ...
    def __rmul__(self, other: list[int]) -> BFVVector: ...
    @overload
    def __add__(self, other: BFVVector) -> BFVVector: ...
    @overload
    def __add__(self, other: list[int]) -> BFVVector: ...

class Context:
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None: ...
    def make_context_public(self) -> None: ...
    def serialize(self) -> bytes: ...
    def secret_key(self) -> SecretKey: ...

def context(*args: t.Any, **kwargs: t.Any) -> Context: ...
def context_from(data: bytes, n_threads: int | None = None) -> Context: ...
def bfv_vector(context: Context | None = None, vector: list[int | None] | None = None) -> BFVVector: ...
def bfv_vector_from(context: Context, data: bytes) -> BFVVector: ...

class SCHEME_TYPE(Enum):
    BFV = ...
