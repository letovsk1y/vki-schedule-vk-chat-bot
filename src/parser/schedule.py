from typing import Optional, List
import aiohttp
import aiofiles
import fitz
from PIL import Image
from bs4 import BeautifulSoup
from vkbottle import PhotoMessageUploader
from src import config


# uploading attachments to vk server
async def upload(uploader: PhotoMessageUploader, pages: int) -> List[str]:
    uploaded_attachments = []
    for i in range(pages):
        uploaded_attachments.append(await uploader.upload(config.PNG_PATH.format(index=i)))
    return uploaded_attachments


# main parse function
async def parse(session: aiohttp.ClientSession, link: Optional[str] = None):
    if not link:
        link = await get_link(session)

    async with session.get(link) as r:
        content = await r.content.read()

    async with aiofiles.open(config.PDF_PATH, "wb") as f:
        await f.write(content)

    pages = await pdf2png(config.PDF_PATH)

    return link, pages


# convert pdf to png
async def pdf2png(filename: str) -> int:
    fz = fitz.Document(filename)
    for i, page in enumerate(fz):
        px: fitz.Pixmap = page.get_pixmap()
        px.pil_save(config.PNG_PATH.format(index=i), bitmap_format="png")

        img = Image.open(config.PNG_PATH.format(index=i))
        # if image resolution > 2k we will reduce it by half
        if px.width > 2560 and px.height > 1440:
            img = img.resize((px.width // 2, px.height // 2))
        img.save(config.PNG_PATH.format(index=i), bitmap_format="png")

    pages = fz.page_count
    fz.close()

    return pages


# parse link to file with schedule
async def get_link(session: aiohttp.ClientSession) -> str:
    async with session.get("https://ci.nsu.ru/education/schedule/") as response:
        html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')
    files = soup.find_all("div", attrs={"class": "file-div"})
    for file in files:
        file_name = file.find_next("div", attrs={"class": "file-name"}).text
        file_link = "https://ci.nsu.ru" + file.find_next("a", attrs={"class": "file-link"}).get("href")

        filtered = True
        for item in config.SCHEDULE_NAME_FILTER:
            if item not in file_name:
                filtered = False
                break
        if filtered:
            break
    else:
        raise KeyError("File link not found")

    return file_link
