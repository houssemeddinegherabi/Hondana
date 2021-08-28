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

from typing import TYPE_CHECKING, Optional, Type, TypeVar, Union

import aiohttp

from .errors import NotFound, UploadInProgress, UploadMangaNotFound
from .http import Route
from .utils import as_chunks


if TYPE_CHECKING:
    from io import BufferedIOBase
    from types import TracebackType

    from .http import HTTPClient
    from .types.upload import UploadBeginResponse, UploadImageResponse

    UploadT = TypeVar("UploadT", bound="ChapterUpload")


class ChapterUpload:
    def __init__(self, *, http: HTTPClient, manga_id: str, scanlator_groups: Optional[list[str]] = None) -> None:
        self.http = http
        self.manga = manga_id
        self.groups = scanlator_groups
        self.pending_chapters: list[str] = []
        self.session_id: Optional[str] = None

    async def __aenter__(self: UploadT) -> UploadT:
        await self.pre_upload_check()
        return self

    async def __aexit__(
        self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]
    ) -> None:
        await self.commit_upload()

    async def pre_upload_check(self) -> None:
        route = Route("GET", "/upload")
        try:
            await self.http.request(route)
        except NotFound:
            # This means no session is in progress
            pass
        else:
            raise UploadInProgress("You already have an open upload session")

        try:
            await self.http._view_manga(self.manga, includes=None)
        except NotFound:
            # The manga you are attempting to upload chapters for does not exist.
            raise UploadMangaNotFound("The target manga has not been found. Please check the ID.")

    async def begin_upload_session(self) -> str:
        data: dict[str, Union[str, list[str]]] = {
            "manga": self.manga,
        }
        if self.groups:
            data["groups"] = self.groups

        route = Route("POST", "/upload/begin")
        response: UploadBeginResponse = await self.http.request(route, data=data)

        session_id = response["data"]["id"]
        self.session_id = session_id
        return session_id

    async def post_images(self, images: list[BufferedIOBase]) -> None:
        route = Route("POST", "/upload/{session_id}", session_id=self.session_id)
        for batch in as_chunks(iter(images), 10):
            form = aiohttp.FormData()
            form.add_field("image", batch)
            data: UploadImageResponse = await self.http.request(
                route, data=form, headers={"Content-Type": "multipart/form-data"}
            )

    async def commit_upload(self) -> None:
        ...
