
import json
import os
import re
import sys
import time
import mimetypes
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

API_BASE = "https://graph.threads.net/v1.0"
XML_FILE = Path("posts.xml")
IDS_FILE = Path("threads_imported_ids.json")
MEDIA_DIR = Path("media")
AVATAR = "pfp/firefox.png"
USERNAME = "bann6r_"
TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")

FIELDS = (
    "id,username,text,timestamp,permalink,media_type,"
    "media_url,thumbnail_url,children,is_quote_post"
)


def api_get(url, params=None):
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Missing THREADS_ACCESS_TOKEN environment variable.")

    if params:
        params = dict(params)
        params["access_token"] = token
        url += ("&" if "?" in url else "?") + urlencode(params)
    elif "access_token=" not in url:
        url += ("&" if "?" in url else "?") + urlencode(
            {"access_token": token}
        )

    request = Request(url, headers={"User-Agent": "bann6r-archive-importer/1.0"})
    try:
        with urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # Don't print the request URL: it can contain the access token.
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Threads API returned HTTP {exc.code}: {body[:1200]}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Threads API: {exc.reason}") from exc


def fetch_all_posts():
    url = f"{API_BASE}/me/threads"
    params = {"fields": FIELDS, "limit": 50}
    posts = []
    seen_cursors = set()

    while url:
        result = api_get(url, params)
        params = None
        posts.extend(result.get("data", []))

        # Follow the API's next-page link without printing it.
        paging = result.get("paging", {})
        next_url = paging.get("next")
        cursor = paging.get("cursors", {}).get("after")

        if not next_url:
            break
        if cursor and cursor in seen_cursors:
            raise RuntimeError("Repeated pagination cursor; stopping safely.")
        if cursor:
            seen_cursors.add(cursor)

        url = next_url

    return posts


def load_ids():
    if not IDS_FILE.exists():
        return set()
    data = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    return set(data.get("ids", []))


def save_ids(ids):
    IDS_FILE.write_text(
        json.dumps({"ids": sorted(ids)}, indent=2) + "\n",
        encoding="utf-8",
    )


def load_archive():
    if not XML_FILE.exists():
        raise FileNotFoundError("posts.xml was not found in the repository root.")

    tree = ET.parse(XML_FILE)
    root = tree.getroot()
    if root.tag != "archive":
        raise RuntimeError(
            f"Expected <archive> as the XML root, got <{root.tag}>."
        )
    return tree, root


def text_of(post, tag):
    element = post.find(tag)
    return (element.text or "").strip() if element is not None else ""


def post_fingerprint(username, date_iso, text):
    # Fallback for older manually archived posts that don't have API IDs.
    return (username.strip().lower(), date_iso, text.strip())


def existing_fingerprints(root):
    fingerprints = set()
    for post in root.findall("post"):
        if text_of(post, "platform") != "threads":
            continue
        date_element = post.find("date")
        date_iso = date_element.get("datetime", "") if date_element is not None else ""
        fingerprints.add(
            post_fingerprint(
                text_of(post, "username"),
                date_iso,
                text_of(post, "text"),
            )
        )
    return fingerprints


def format_date(timestamp):
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    local_date = parsed.astimezone(TIMEZONE).date()
    return local_date.isoformat(), local_date.strftime("%d/%m/%Y")


def download_media(url, post_id, index):
    if not url:
        return None

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "bann6r-archive-importer/1.0"})

    try:
        with urlopen(request, timeout=45) as response:
            content_type = response.headers.get_content_type()
            content = response.read()
    except (HTTPError, URLError) as exc:
        print(f"Warning: couldn't download media for post {post_id}: {exc}")
        return None

    if not content:
        return None

    extension = mimetypes.guess_extension(content_type) or ".bin"
    if extension == ".jpe":
        extension = ".jpg"

    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", post_id)
    filename = f"threads_{safe_id}_{index}{extension}"
    path = MEDIA_DIR / filename
    path.write_bytes(content)
    return path.as_posix()


def get_media_urls(post):
    urls = []
    media_type = post.get("media_type", "")

    if media_type in ("IMAGE", "VIDEO") and post.get("media_url"):
        urls.append(post["media_url"])
    elif media_type == "CAROUSEL_ALBUM":
        children = post.get("children", {}).get("data", [])
        for child in children:
            child_id = child.get("id")
            if not child_id:
                continue
            try:
                details = api_get(
                    f"{API_BASE}/{child_id}",
                    {"fields": "id,media_type,media_url,thumbnail_url"},
                )
            except RuntimeError as exc:
                print(f"Warning: couldn't retrieve carousel item: {exc}")
                continue

            media_url = details.get("media_url") or details.get("thumbnail_url")
            if media_url:
                urls.append(media_url)

    # A video thumbnail is more useful for a still-image archive than the video.
    elif media_type == "VIDEO" and post.get("thumbnail_url"):
        urls.append(post["thumbnail_url"])

    return urls


def make_xml_post(api_post, fingerprints):
    post_id = str(api_post.get("id", "")).strip()
    username = api_post.get("username") or USERNAME
    content = api_post.get("text") or ""

    if not post_id:
        return None, None

    if not api_post.get("timestamp"):
        print(f"Skipping post {post_id}: no timestamp returned.")
        return None, None

    date_iso, date_display = format_date(api_post["timestamp"])
    fingerprint = post_fingerprint(username, date_iso, content)

    element = ET.Element("post")
    ET.SubElement(element, "username").text = username
    ET.SubElement(element, "platform").text = "threads"

    date_element = ET.SubElement(element, "date", {"datetime": date_iso})
    date_element.text = date_display

    ET.SubElement(element, "avatar").text = AVATAR
    ET.SubElement(element, "text").text = content

    media_urls = get_media_urls(api_post)
    downloaded = []
    for index, media_url in enumerate(media_urls, start=1):
        local_path = download_media(media_url, post_id, index)
        if local_path:
            downloaded.append(local_path)

    if downloaded:
        images_element = ET.SubElement(element, "images")
        for local_path in downloaded:
            ET.SubElement(images_element, "image").text = local_path

    # The current XML schema doesn't need to change to store the API ID.
    return element, fingerprint


def indent_xml(root):
    # Pretty-print XML on Python versions that support it.
    if hasattr(ET, "indent"):
        ET.indent(root, space="    ")


def main():
    tree, root = load_archive()
    imported_ids = load_ids()
    fingerprints = existing_fingerprints(root)

    posts = fetch_all_posts()
    # Process older posts first so new entries are appended chronologically.
    posts.sort(key=lambda post: post.get("timestamp", ""))

    added = 0
    for api_post in posts:
        post_id = str(api_post.get("id", "")).strip()
        if not post_id or post_id in imported_ids:
            continue

        username = api_post.get("username") or USERNAME
        content = api_post.get("text") or ""
        timestamp = api_post.get("timestamp")
        if not timestamp:
            continue
        date_iso, _ = format_date(timestamp)
        fingerprint = post_fingerprint(username, date_iso, content)

        # Mark existing matching posts as seen without duplicating them.
        if fingerprint in fingerprints:
            imported_ids.add(post_id)
            continue

        xml_post, fingerprint = make_xml_post(api_post, fingerprints)
        if xml_post is None:
            continue

        root.append(xml_post)
        fingerprints.add(fingerprint)
        imported_ids.add(post_id)
        added += 1
        print(f"Imported Threads post {post_id}")

    indent_xml(root)
    tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)
    save_ids(imported_ids)

    print(
        f"Finished: {added} new post(s) added; "
        f"{len(posts)} API post(s) checked."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        sys.exit(1)
