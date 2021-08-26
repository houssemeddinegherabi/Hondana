import asyncio

import hondana


client = hondana.Client(username="...", password="...")


async def main():
    async with client.upload_chapter("your-manga-id-here", scanlator_groups=["...", "..."]) as upload:
        session_id = await upload.begin_upload_session()
        # We're going to assume you have a list of file-like objects ready, e.g. the bytes of images...
        list_of_pages = []  # This is a list of 26 pages.
        await upload.post_images(list_of_pages)
