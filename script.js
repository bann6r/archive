
const platformIcons = {
    threads: "icons/threads.svg",
    bsky: "icons/bsky.svg"
};

function getText(element, selector) {
    return element.querySelector(selector)?.textContent.trim() || "";
}

function createPlatformIcon(platformName, className) {
    const platform = document.createElement("span");
    platform.className = className;

    // Set custom tooltip text based on the platform
    if (platformName === "threads") {
        platform.title = "this is posted via threads.";
    } else if (platformName === "bsky") {
        platform.title = "threads is notorious for restricting content related to suicide/self-harm for users under 18. the only workaround is to use bsky. since i only shared the bsky link in the threads post, the post will appear as a bsky post.";
    }

    const iconPath = platformIcons[platformName];

    if (iconPath) {
        const icon = document.createElement("img");
        icon.src = iconPath;
        icon.alt = `Posted on ${platformName}`;
        platform.appendChild(icon);
    }

    return platform;
}

function createHeader(post, quoted = false) {
    const header = document.createElement("header");
    header.className = quoted ? "quoted-post-header" : "post-header";

    const usernameText = getText(post, "username");
    const avatarPath = getText(post, "avatar");
    const platformName = getText(post, "platform").toLowerCase();

    const avatar = document.createElement("img");
    avatar.className = quoted ? "quoted-post-avatar" : "avatar";
    avatar.src = avatarPath || "pfp/placeholder.png";
    avatar.alt = usernameText
    ? `${usernameText}'s profile picture`
    : "Profile picture";
    avatar.loading = "lazy";

    const headerContent = document.createElement("div");
    headerContent.className = quoted
    ? "quoted-post-author"
    : "header-content";

    const headerRow = document.createElement("div");
    headerRow.className = quoted
    ? "quoted-post-author-row"
    : "header-row";

    const username = document.createElement("span");
    username.className = quoted ? "quoted-post-username" : "username";
    username.textContent = usernameText;

    const date = document.createElement("time");
    date.className = quoted ? "quoted-post-date" : "date";

    const dateElement = post.querySelector("date");
    date.textContent = dateElement?.textContent.trim() || "";

    if (dateElement?.getAttribute("datetime")) {
        date.dateTime = dateElement.getAttribute("datetime");
    }

    const platform = createPlatformIcon(
        platformName,
        quoted ? "quoted-post-platform" : "platform"
    );

    headerRow.append(username, date, platform);
    headerContent.appendChild(headerRow);
    header.append(avatar, headerContent);

    return header;
}

function createQuote(quoteElement) {
    const quote = document.createElement("div");
    quote.className = "quoted-post";

    quote.appendChild(createHeader(quoteElement, true));

    const quoteText = getText(quoteElement, "text");

    if (quoteText) {
        const text = document.createElement("div");
        text.className = "quoted-post-content";
        text.textContent = quoteText;
        quote.appendChild(text);
    }

    return quote;
}

function createImages(post, content) {
    const images = post.querySelectorAll(":scope > images > image");

    if (images.length === 1) {
        const image = document.createElement("img");
        image.className = "post-single-image";
        image.src = images[0].textContent.trim();
        image.alt = "Image attached to post";
        image.loading = "lazy";

        content.appendChild(image);
    } else if (images.length > 1) {
        const carousel = document.createElement("div");
        carousel.className = "post-carousel";

        const track = document.createElement("div");
        track.className = "carousel-track";
        track.setAttribute("aria-label", "Post images");

        // Preserve image order from posts.xml.
        images.forEach((imageElement, imageIndex) => {
            const slide = document.createElement("div");
            slide.className = "carousel-slide";

            const image = document.createElement("img");
            image.src = imageElement.textContent.trim();
            image.alt = `Image ${imageIndex + 1} of ${images.length}`;
            image.loading = imageIndex === 0 ? "eager" : "lazy";
            image.draggable = false;

            slide.appendChild(image);
            track.appendChild(slide);
        });

        carousel.appendChild(track);

        const previous = document.createElement("button");
        previous.className = "carousel-arrow carousel-previous";
        previous.type = "button";
        previous.textContent = "‹";
        previous.setAttribute("aria-label", "Previous image");
        previous.hidden = true;

        const next = document.createElement("button");
        next.className = "carousel-arrow carousel-next";
        next.type = "button";
        next.textContent = "›";
        next.setAttribute("aria-label", "Next image");

        const updateArrows = () => {
            const maxScroll = track.scrollWidth - track.clientWidth;

            previous.hidden = track.scrollLeft <= 2;
            next.hidden =
            maxScroll <= 2 ||
            track.scrollLeft >= maxScroll - 2;
        };

        previous.addEventListener("click", () => {
            track.scrollBy({
                left: -track.clientWidth,
                behavior: "smooth"
            });
        });

        next.addEventListener("click", () => {
            track.scrollBy({
                left: track.clientWidth,
                behavior: "smooth"
            });
        });

        track.addEventListener("scroll", updateArrows);
        window.addEventListener("resize", updateArrows);

        carousel.append(previous, next);
        content.appendChild(carousel);

        requestAnimationFrame(updateArrows);

        track.querySelectorAll("img").forEach((image) => {
            image.addEventListener("load", updateArrows, { once: true });
        });
    }
}

function createVideo(post, content) {
    const videoPath = getText(post, ":scope > video");

    if (!videoPath) return;

    const video = document.createElement("video");
    video.className = "post-video";
    video.controls = true;
    video.preload = "metadata";
    video.playsInline = true;

    const source = document.createElement("source");
    source.src = videoPath;
    source.type = "video/mp4";

    video.appendChild(source);
    content.appendChild(video);
}

function createActions(content) {
    const actions = document.createElement("div");
    actions.className = "actions";
    actions.setAttribute("aria-label", "Post actions");

    const actionIcons = [
        ["Like", "icons/love.svg"],
        ["Comment", "icons/comment.svg"],
        ["Repost", "icons/repost.svg"]
    ];

    actionIcons.forEach(([label, src]) => {
        const action = document.createElement("span");
        action.className = "action";
        action.title = label;

        const icon = document.createElement("img");
        icon.src = src;
        icon.alt = "";

        action.appendChild(icon);
        actions.appendChild(action);
    });

    content.appendChild(actions);
}

function createPost(post) {
    const article = document.createElement("article");
    article.className = "post";

    article.appendChild(createHeader(post));

    const content = document.createElement("div");
    content.className = "post-content";

    const postText = getText(post, ":scope > text");

    // Image-only posts are allowed.
    if (postText) {
        const text = document.createElement("p");
        text.className = "post-text";
        text.textContent = postText;
        content.appendChild(text);
    }

    createImages(post, content);
    createVideo(post, content);

    const quoteElement = post.querySelector(":scope > quote");

    if (quoteElement) {
        content.appendChild(createQuote(quoteElement));
    }

    createActions(content);

    // Optional author's/archiver's note, below the action icons
    const noteText = getText(post, ":scope > note, :scope > author-note, :scope > author_note");

    if (noteText) {
        const note = document.createElement("aside");
        note.className = "archivers-note";
        note.setAttribute("aria-label", "Author's note");
        note.textContent = noteText;
        content.appendChild(note);
    }

    article.appendChild(content);
    return article;
}

async function loadArchive() {
    const response = await fetch("posts.xml");

    if (!response.ok) {
        throw new Error(`Could not load posts.xml: ${response.status}`);
    }

    const xmlText = await response.text();
    const xml = new DOMParser().parseFromString(
        xmlText,
        "application/xml"
    );

    if (xml.querySelector("parsererror")) {
        document.querySelector("#archive").textContent =
        "Could not read posts.xml. Please check its XML formatting.";
        return;
    }

    const archive = document.querySelector("#archive");
    const posts = xml.querySelectorAll("archive > post");

    posts.forEach((post, index) => {
        if (index > 0) {
            const divider = document.createElement("hr");
            divider.className = "post-divider";
            archive.appendChild(divider);
        }

        archive.appendChild(createPost(post));
    });
}

loadArchive().catch((error) => {
    console.error("Archive loading failed:", error);
    document.querySelector("#archive").textContent =
    "ERROR: Could not load the archive. Check the browser console.";
});
