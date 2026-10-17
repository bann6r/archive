
from pathlib import Path
from datetime import date, datetime
import xml.etree.ElementTree as ET

MEDIA_DIR = Path("media")
OUTPUT_FILE = Path("generated_post.xml")

ACCOUNTS = {
    "1": {
        "name": "New Threads",
        "username": "bann6r_",
        "platform": "threads",
        "avatar": "pfp/firefox.png",
    },
    "2": {
        "name": "Old Threads (archive)",
        "username": "bann6r",
        "platform": "threads",
        "avatar": "pfp/firefox.png",  # Change if the old avatar differs
    },
    "3": {
        "name": "Bluesky",
        "username": "bann6r.github.io",
        "platform": "bsky",
        "avatar": "pfp/bsky_threads_2.png",
    },
}


def choose_account():
    print("\nChoose an account:")
    for key, account in ACCOUNTS.items():
        print(f"  {key}. {account['name']} (@{account['username']})")

    while True:
        choice = input("> ").strip()

        if choice in ACCOUNTS:
            return ACCOUNTS[choice]

        print("Please choose 1, 2, or 3.")


def ask_multiline():
    print("\nEnter your post caption.")
    print("Press Enter on an empty line to finish.")
    print("Leave it empty for an image-only post.\n")

    lines = []

    while True:
        line = input()
        if line == "":
            break
        lines.append(line)

    return "\n".join(lines)


def ask_date():
    while True:
        date_input = input(
            "\nPost date (YYYY-MM-DD, blank for today): "
        ).strip()

        if not date_input:
            return date.today()

        try:
            return datetime.strptime(
                date_input, "%Y-%m-%d"
            ).date()
        except ValueError:
            print("Invalid date. Please use YYYY-MM-DD.")


def ask_images():
    while True:
        answer = input(
            "\nDoes it have images? [y/n]: "
        ).strip().lower()

        if answer in ("y", "n"):
            break

        print("Please enter y or n.")

    if answer == "n":
        return []

    images = []

    print(f"\nEnter image filenames from {MEDIA_DIR}/")
    print("Add as many as you need, in display order.")
    print("Press Enter on an empty line when finished.")

    while True:
        filename = input("> ").strip()

        if not filename:
            break

        path = Path(filename)

        # Only accept filenames, not paths or directory traversal.
        if path.name != filename or filename in (".", ".."):
            print("Enter only the filename, not a folder path.")
            continue

        full_path = MEDIA_DIR / filename

        if not full_path.is_file():
            print(f"File not found: {full_path}")
            continue

        relative_path = (MEDIA_DIR / filename).as_posix()

        if relative_path in images:
            print("That image has already been added.")
            continue

        images.append(relative_path)
        print(f"Added: {filename}")

    return images


def build_post(account, content, post_date, images):
    post = ET.Element("post")

    ET.SubElement(post, "username").text = account["username"]
    ET.SubElement(post, "platform").text = account["platform"]

    date_element = ET.SubElement(
        post, "date", {"datetime": post_date.isoformat()}
    )
    date_element.text = post_date.strftime("%d/%m/%Y")

    ET.SubElement(post, "avatar").text = account["avatar"]
    ET.SubElement(post, "text").text = content

    if images:
        images_element = ET.SubElement(post, "images")

        for image_path in images:
            ET.SubElement(images_element, "image").text = image_path

    ET.indent(post, space="    ")
    return post


def main():
    print("=== Social Post XML Generator ===")

    account = choose_account()
    content = ask_multiline()
    post_date = ask_date()
    images = ask_images()

    # A post must have a caption or at least one image.
    if not content.strip() and not images:
        print("\nError: A post needs a caption or at least one image.")
        print("Nothing was saved.")
        return

    post = build_post(account, content, post_date, images)

    xml_output = ET.tostring(
        post,
        encoding="unicode",
        short_empty_elements=True,
    )

    print("\n=== Generated XML ===\n")
    print(xml_output)

    OUTPUT_FILE.write_text(xml_output + "\n", encoding="utf-8")

    print(f"\nSaved to {OUTPUT_FILE}")
    print("Copy the <post> block into posts.xml.")


if __name__ == "__main__":
    main()
