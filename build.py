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
import os
import pathlib
import re
import datetime

# Override for local preview:  SITE_BASE_URL=http://localhost:4599 python3 build.py
BASE_URL = os.environ.get("SITE_BASE_URL", "https://www.campanilelabs.com").rstrip("/")
ROOT = pathlib.Path(__file__).parent
CONTENT = ROOT / "parts" / "content"
TODAY = datetime.date.today().isoformat()

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
        extra_head='''    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Blog","name":"campanile Labs Blog","url":"%s/blog.html","publisher":{"@type":"Organization","name":"campanile Labs"}}
    </script>''' % BASE_URL,
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
}

# Extra URLs for the sitemap that aren't built here (hand-maintained).
STATIC_URLS = ["index.html"]


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


def main() -> None:
    print("building pages:")
    for path, meta in PAGES.items():
        build_page(path, meta)
    build_sitemap()
    build_robots()
    print("done.")


if __name__ == "__main__":
    main()
