"""
The MIT License (MIT)

Copyright (c) 2021-Present AbstractUmbra

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
from __future__ import annotations

import json
import pathlib
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Iterator,
    Mapping,
    Optional,
    TypeVar,
    Union,
    overload,
)

from .errors import AuthenticationRequired


if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec

    from .client import Client


C = TypeVar("C", bound="Client")
T = TypeVar("T")
Y = TypeVar("Y")
_Iter = Union[Iterator[Y], AsyncIterator[Y]]
if TYPE_CHECKING:
    B = ParamSpec("B")


__all__ = ("MISSING", "to_json", "php_query_builder", "TAGS")

_PROJECT_DIR = pathlib.Path(__file__)


class MissingSentinel:
    def __eq__(self, _: Any) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."


MISSING: Any = MissingSentinel()


def require_authentication(func: Callable[Concatenate[C, B], T]) -> Callable[Concatenate[C, B], T]:
    @wraps(func)
    def wrapper(client: C, *args: B.args, **kwargs: B.kwargs) -> T:
        if not client._http._authenticated:
            raise AuthenticationRequired("This method requires you to be authenticated to the API.")

        return func(client, *args, **kwargs)

    return wrapper


def to_json(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)


def php_query_builder(obj: Mapping[str, Optional[Union[str, int, bool, list[str], dict[str, str]]]]) -> str:
    """
    {"order": {"publishAt": "desc"}, "translatedLanguages": ["en", "jp"]}
    ->
    "order[publishAt]=desc&translatedLanguages[]=en&translatedLanguages[]=jp"
    """
    fmt = []
    for key, value in obj.items():
        if value is None or value is MISSING:
            fmt.append(f"{key}=null")
        if isinstance(value, (str, int, bool)):
            fmt.append(f"{key}={str(value)}")
        elif isinstance(value, list):
            fmt.extend(f"{key}[]={item}" for item in value)
        elif isinstance(value, dict):
            fmt.extend(f"{key}[{subkey}]={subvalue}" for subkey, subvalue in value.items())

    return "&".join(fmt)


def _chunk(iterator: Iterator[Y], max_size: int) -> Iterator[list[Y]]:
    ret = []
    n = 0
    for item in iterator:
        ret.append(item)
        n += 1
        if n == max_size:
            yield ret
            ret = []
            n = 0
    if ret:
        yield ret


async def _achunk(iterator: AsyncIterator[Y], max_size: int) -> AsyncIterator[list[Y]]:
    ret = []
    n = 0
    async for item in iterator:
        ret.append(item)
        n += 1
        if n == max_size:
            yield ret
            ret = []
            n = 0
    if ret:
        yield ret


@overload
def as_chunks(iterator: Iterator[Y], max_size: int) -> Iterator[list[Y]]:
    ...


@overload
def as_chunks(iterator: AsyncIterator[Y], max_size: int) -> AsyncIterator[list[Y]]:
    ...


def as_chunks(iterator: _Iter[Y], max_size: int) -> _Iter[list[Y]]:
    """A helper function that collects an iterator into chunks of a given size.
    .. versionadded:: 2.0
    Parameters
    ----------
    iterator: Union[:class:`collections.abc.Iterator`, :class:`collections.abc.AsyncIterator`]
        The iterator to chunk, can be sync or async.
    max_size: :class:`int`
        The maximum chunk size.
    .. warning::
        The last chunk collected may not be as large as ``max_size``.
    Returns
    --------
    Union[:class:`Iterator`, :class:`AsyncIterator`]
        A new iterator which yields chunks of a given size.
    """
    if max_size <= 0:
        raise ValueError("Chunk sizes must be greater than 0.")

    if isinstance(iterator, AsyncIterator):
        return _achunk(iterator, max_size)
    return _chunk(iterator, max_size)


path: pathlib.Path = _PROJECT_DIR.parent / "extras" / "tags.json"
with open(path, "r") as _fp:
    TAGS: dict[str, list[str]] = json.load(_fp)
