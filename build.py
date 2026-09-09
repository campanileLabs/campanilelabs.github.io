#!/usr/bin/env python3
"""
campanile Labs static-site build.

Content lives in parts/content/**.  This script wraps each fragment in a full,
crawlable HTML document (own <head>, <title>, description, canonical, Open Graph,
inlined header/footer nav) and writes it to the public path Google indexes.
It also (re)generates sitemap.xml and robots.txt.

Run after editing anything in parts/ or adding a blog post:

    python3 build.py

index.html is hand-maintained (the WebGPU canvas homepage) and is NOT touched
here, but it is still listed in the sitemap.
"""

import html
import json
import os
import pathlib
import re
import datetime

# Override for local preview:  SITE_BASE_URL=http://localhost:4599 python3 build.py
BASE_URL = os.environ.get("SITE_BASE_URL", "https://www.campanilelabs.com").rstrip("/")
ROOT = pathlib.Path(__file__).parent
CONTENT = ROOT / "parts" / "content"
TODAY = datetime.date.today().isoformat()

DEFAULT_OG_IMAGE = BASE_URL + "/img/campanileLabs.png"
DEFAULT_KEYWORDS = (
    "campanile Labs, multimedia software, video, audio, image, "
    "macOS apps, open source, Edsel Malasig"
)

HEADER = (ROOT / "parts" / "header.html").read_text(encoding="utf-8").strip()
FOOTER = (ROOT / "parts" / "footer.html").read_text(encoding="utf-8").strip()

GTM_HEAD = """    <!-- Google Tag Manager -->
    <script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
    new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
    j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
    'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
    })(window,document,'script','dataLayer','GTM-WBLGCJ85');</script>
    <script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
    new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
    j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
    'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
    })(window,document,'script','dataLayer','GTM-NMR75RR9');</script>
    <!-- End Google Tag Manager -->"""

GTM_BODY = """    <!-- Google Tag Manager (noscript) -->
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-WBLGCJ85"
    height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-NMR75RR9"
    height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
    <!-- End Google Tag Manager (noscript) -->"""

SHELL_CSS = """    body { font-family: Arial, sans-serif; margin: 20px; background-color: #faf7f0; }
    .div_container {
        display: grid;
        grid-template-columns: clamp(0px, 15%, 200px) 1fr clamp(0px, 15%, 200px);
        width: 100%;
        min-height: 55vh;
    }
    .div_left, .div_right { width: 100%; }
    .div_middle { width: 100%; }
    h1 { font-size: 28px; color: #333; }
    @media (max-width: 600px) {
        body { margin: 10px; }
        .div_container { grid-template-columns: 1fr; }
    }"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
{gtm_head}

    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta name="keywords" content="{keywords}">
    <meta name="robots" content="index, follow">
    <meta name="googlebot" content="index, follow, max-image-preview:large, max-snippet:-1">
    <link rel="canonical" href="{canonical}">

    <meta property="og:type" content="{og_type}">
    <meta property="og:site_name" content="campanile Labs">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:image" content="{og_image}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{og_image}">
{extra_head}
    <style>
{shell_css}
    </style>
</head>
<body>
{gtm_body}

{header}

    <div class="div_container">
        <div class="div_left"></div>
        <main class="div_middle">
{content}
        </main>
        <div class="div_right"></div>
    </div>

{footer}
</body>
</html>
"""

# path (public, relative to site root) -> page metadata
PAGES = {
    "apps.html": dict(
        src="apps.html",
        title="Apps — campanile Labs",
        description="Small, feature-rich apps for video, sound, and image from campanile Labs: playful Veo, reVid, sonido Diseno, Audioforma, and Imagen.",
        keywords="playful Veo, reVid, sonido Diseno, Audioforma, Imagen, video-filter app, video editing software, sound design app, audio visualizer, image editor, real-time video effects, macOS multimedia apps",
    ),
    "oss.html": dict(
        src="oss.html",
        title="Open Source — campanile Labs",
        description="The open-source libraries the campanile Labs apps are built on — FFmpeg, Dear ImGui, Vulkan, RtAudio, FFTW3 and more — and their licenses.",
    ),
    "blog.html": dict(
        src="blog.html",
        title="Blog — campanile Labs",
        description="Notes from the workshop at campanile Labs: build logs and first looks at the apps and experiments, newest first.",
        keywords="campanile Labs blog, playful Veo, Audioforma, one-yolo-coreml, Haiku OS, CoreML YOLO, audio visualization, video effects, build log, indie software development",
        # extra_head (Blog + BlogPosting list JSON-LD) is filled in below,
        # generated from the blog/* entries so it never drifts out of sync.
    ),
    "about.html": dict(
        src="about.html",
        title="About — campanile Labs",
        description="campanile Labs is a one-person experimental software lab in California run by Edsel Malasig, building multimedia tools for image, 3D, audio, and video.",
    ),
    "apps/audioforma.html": dict(
        src="apps/audioforma.html",
        title="Audioforma — campanile Labs",
        description="Audioforma, an audio app from campanile Labs.",
    ),
    "apps/sonidodiseno.html": dict(
        src="apps/sonidodiseno.html",
        title="sonido Diseno — campanile Labs",
        description="sonido Diseno, a sound-design app from campanile Labs.",
    ),
    "apps/imagen.html": dict(
        src="apps/imagen.html",
        title="Imagen — campanile Labs",
        description="Imagen, an image app from campanile Labs.",
    ),
    "apps/playfulVeo.html": dict(
        src="apps/playfulVeo.html",
        title="playful Veo — campanile Labs",
        description="playful Veo, a real-time video-filter playground from campanile Labs.",
    ),
    "apps/revid.html": dict(
        src="apps/revid.html",
        title="reVid — campanile Labs",
        description="reVid, a video-editing app from campanile Labs.",
    ),
    "blog/blog_00001.html": dict(
        src="blog/blog_00001.html",
        title="A first look at the playful Veo interface — campanile Labs",
        description="Where playful Veo stands today: one drop target, seven real-time filters (mosaic, hex heat-map, chromatic glitch, halftone, shuffled tiles, edge trace) running live while a clip plays.",
        og_type="article",
        og_image=BASE_URL + "/media/playful-veo-screenshot-1.png",
        extra_head='''    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"BlogPosting","headline":"A first look at the playful Veo interface","datePublished":"2026-09-07","dateModified":"2026-09-07","author":{"@type":"Person","name":"Edsel Malasig"},"publisher":{"@type":"Organization","name":"campanile Labs"},"image":"%s/media/playful-veo-screenshot-1.png","mainEntityOfPage":"%s/blog/blog_00001.html"}
    </script>''' % (BASE_URL, BASE_URL),
    ),
    "blog/blog_00002.html": dict(
        src="blog/blog_00002.html",
        title="one-yolo-coreml: fanning a single CoreML model across many feeds — campanile Labs",
        description="A small experiment: run one YOLO detector compiled to CoreML against a wall of dashcam streams on Apple Silicon — six feeds hold ~54 FPS each, eight still clear real-time.",
        og_type="article",
        og_image=BASE_URL + "/media/one-yolo-coreml-1.jpg",
        extra_head='''    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"BlogPosting","headline":"one-yolo-coreml: fanning a single CoreML model across many feeds","datePublished":"2026-09-07","dateModified":"2026-09-07","author":{"@type":"Person","name":"Edsel Malasig"},"publisher":{"@type":"Organization","name":"campanile Labs"},"image":"%s/media/one-yolo-coreml-1.jpg","mainEntityOfPage":"%s/blog/blog_00002.html"}
    </script>''' % (BASE_URL, BASE_URL),
    ),
    "blog/blog_00003.html": dict(
        src="blog/blog_00003.html",
        title="Haiku OS launches like a rocket on qemu and on my Mac — campanile Labs",
        description="Look at the size of the Haiku OS image — it is tiny and still performs well. No graphics acceleration yet and emulator-only, but progress toward release is fast and it looks promising. Time to start contributing.",
        og_type="article",
        og_image=BASE_URL + "/media/haiku-os-2.jpg",
        extra_head='''    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"BlogPosting","headline":"Haiku OS launches like a rocket on qemu and on my Mac","datePublished":"2026-09-08","dateModified":"2026-09-08","author":{"@type":"Person","name":"Edsel Malasig"},"publisher":{"@type":"Organization","name":"campanile Labs"},"image":"%s/media/haiku-os-2.jpg","mainEntityOfPage":"%s/blog/blog_00003.html"}
    </script>''' % (BASE_URL, BASE_URL),
    ),
    "blog/blog_00004.html": dict(
        src="blog/blog_00004.html",
        title="An early look at Audioforma — campanile Labs",
        description="An early look at Audioforma, an audio-visualization and video-generation app built from open-source libraries with the help of Claude AI: audio in, a reactive animated scene, video out.",
        og_type="article",
        og_image=BASE_URL + "/media/audioforma-early-look.jpg",
        extra_head='''    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"BlogPosting","headline":"An early look at Audioforma","datePublished":"2026-09-09","dateModified":"2026-09-09","author":{"@type":"Person","name":"Edsel Malasig"},"publisher":{"@type":"Organization","name":"campanile Labs"},"image":"%s/media/audioforma-early-look.jpg","mainEntityOfPage":"%s/blog/blog_00004.html","video":{"@type":"VideoObject","name":"Audioforma, early look","description":"Audioforma turning a track into a reactive spectrum-and-waveform scene and rendering it to video.","thumbnailUrl":"%s/media/audioforma-early-look.jpg","contentUrl":"%s/media/audioforma-early-look.mp4","uploadDate":"2026-09-09","duration":"PT3M26S"}}
    </script>''' % (BASE_URL, BASE_URL, BASE_URL, BASE_URL),
    ),
}

# ---------------------------------------------------------------------------
# Structured data (JSON-LD), assembled from the tables above so it stays in
# sync with the pages themselves.  apps.html gets an ItemList of the apps;
# blog.html gets a Blog with the full BlogPosting list.
# ---------------------------------------------------------------------------

APPS = [
    ("playful Veo",   "playfulVeo.html",   "Real-time video-filter playground."),
    ("reVid",         "revid.html",        "Video-editing app."),
    ("sonido Diseno", "sonidodiseno.html", "Sound-design app."),
    ("Audioforma",    "audioforma.html",   "Audio visualizer that renders to video."),
    ("Imagen",        "imagen.html",       "Image editor."),
]


def jsonld_script(obj: dict) -> str:
    """One <script type=application/ld+json> block, indented to match the head."""
    return ('    <script type="application/ld+json">\n    '
            + json.dumps(obj, ensure_ascii=False)
            + '\n    </script>')


def apps_itemlist() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "campanile Labs apps",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": {
                    "@type": "SoftwareApplication",
                    "name": name,
                    "applicationCategory": "MultimediaApplication",
                    "operatingSystem": "macOS",
                    "url": f"{BASE_URL}/apps/{slug}",
                    "description": desc,
                    "author": {"@type": "Organization", "name": "campanile Labs"},
                },
            }
            for i, (name, slug, desc) in enumerate(APPS)
        ],
    }


def blog_jsonld() -> dict:
    posts = []
    for path, meta in PAGES.items():
        if not path.startswith("blog/"):
            continue
        m = re.search(r'"datePublished":"([\d-]+)"', meta.get("extra_head", ""))
        posts.append({
            "@type": "BlogPosting",
            "headline": meta["title"].rsplit(" — ", 1)[0],
            "url": f"{BASE_URL}/{path}",
            "datePublished": m.group(1) if m else TODAY,
            "image": meta.get("og_image", DEFAULT_OG_IMAGE),
            "author": {"@type": "Person", "name": "Edsel Malasig"},
        })
    posts.sort(key=lambda p: p["datePublished"], reverse=True)
    return {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "campanile Labs Blog",
        "url": f"{BASE_URL}/blog.html",
        "publisher": {"@type": "Organization", "name": "campanile Labs"},
        "blogPost": posts,
    }


PAGES["apps.html"]["extra_head"] = jsonld_script(apps_itemlist())
PAGES["blog.html"]["extra_head"] = jsonld_script(blog_jsonld())


# Extra URLs for the sitemap that aren't built here (hand-maintained).
STATIC_URLS = ["index.html"]

# GitHub Pages custom domain.  Without this file GitHub also serves the site at
# <user>.github.io with no redirect, and Google indexes that instead.  Derived
# from BASE_URL so it always matches the canonical host.
CNAME_HOST = re.sub(r"^https?://", "", BASE_URL).split("/")[0]


# Leave these alone when rooting URLs: already absolute, already root-relative,
# in-page anchors, or non-navigable schemes.
_URL_SKIP = re.compile(r'^(?:https?:|//|/|#|data:|blob:|mailto:|tel:|javascript:)', re.I)


def rootify_urls(text: str) -> str:
    """Rewrite every project-relative URL to a root-relative one (/path)."""
    def attr(m):
        name, quote, val = m.group(1), m.group(2), m.group(3)
        if not val or _URL_SKIP.match(val):
            return m.group(0)
        return f'{name}={quote}/{val}{quote}'

    # src / href / poster / data-src / data-poster  (lookbehind stops "data-src"
    # from also matching the bare "src" inside it)
    text = re.sub(
        r'(?<![\w-])(data-src|data-poster|src|href|poster)=(["\'])([^"\']*)\2',
        attr, text)

    def css_url(m):
        quote, val = m.group(1), m.group(2)
        if not val or _URL_SKIP.match(val):
            return m.group(0)
        return f'url({quote}/{val}{quote})'

    text = re.sub(r'url\(\s*(["\']?)([^)"\']*)\1\s*\)', css_url, text)
    return text


def rewrite_fragment(text: str) -> str:
    """Turn SPA fragment links into plain root-relative page links."""
    # href="?view=foo/bar.html"  ->  href="foo/bar.html"  (rootified below)
    text = re.sub(r'href="\?view=([^"]+)"', r'href="\1"', text)
    text = re.sub(r"href='\?view=([^']+)'", r"href='\1'", text)
    # drop the SPA hook attribute
    text = re.sub(r'\s+data-middle="[^"]*"', "", text)
    text = re.sub(r"\s+data-middle='[^']*'", "", text)
    return rootify_urls(text)


def indent(block: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in block.splitlines())


def build_page(path: str, meta: dict) -> None:
    src = CONTENT / meta["src"]
    fragment = rewrite_fragment(src.read_text(encoding="utf-8").strip())
    canonical = f"{BASE_URL}/{path}"
    doc = PAGE_TEMPLATE.format(
        gtm_head=GTM_HEAD,
        gtm_body=GTM_BODY,
        shell_css=SHELL_CSS,
        title=html.escape(meta["title"], quote=True),
        description=html.escape(meta["description"], quote=True),
        keywords=html.escape(meta.get("keywords", DEFAULT_KEYWORDS), quote=True),
        canonical=canonical,
        og_type=meta.get("og_type", "website"),
        og_image=meta.get("og_image", BASE_URL + "/img/campanileLabs.png"),
        extra_head=meta.get("extra_head", ""),
        header=indent(rootify_urls(HEADER), 4),
        footer=indent(rootify_urls(FOOTER), 4),
        content=indent(fragment, 12),
    )
    out = ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"  wrote {path}")


def build_sitemap() -> None:
    urls = STATIC_URLS + list(PAGES.keys())
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        loc = f"{BASE_URL}/" if u == "index.html" else f"{BASE_URL}/{u}"
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{TODAY}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  wrote sitemap.xml")


def build_robots() -> None:
    txt = (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n"
    )
    (ROOT / "robots.txt").write_text(txt, encoding="utf-8")
    print("  wrote robots.txt")


def build_cname() -> None:
    # Skip when BASE_URL is overridden for a local preview.
    if "localhost" in CNAME_HOST or "127.0.0.1" in CNAME_HOST:
        print("  skipped CNAME (local preview base URL)")
        return
    (ROOT / "CNAME").write_text(CNAME_HOST + "\n", encoding="utf-8")
    print("  wrote CNAME")


def main() -> None:
    print("building pages:")
    for path, meta in PAGES.items():
        build_page(path, meta)
    build_sitemap()
    build_robots()
    build_cname()
    print("done.")


if __name__ == "__main__":
    main()
