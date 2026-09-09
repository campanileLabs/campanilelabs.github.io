# Building the site

The public pages are **generated**. Do not hand-edit `apps.html`, `oss.html`,
`blog.html`, `about.html`, `apps/*.html`, or `blog/*.html` directly — your changes
will be overwritten on the next build.

## Sources

| You edit | It generates |
|----------|--------------|
| `parts/content/apps.html`, `oss.html`, `blog.html`, `about.html` | `/apps.html`, `/oss.html`, `/blog.html`, `/about.html` |
| `parts/content/apps/*.html` | `/apps/*.html` |
| `parts/content/blog/*.html` | `/blog/*.html` |
| `parts/header.html`, `parts/footer.html` | the nav on every generated page |
| `build.py` `PAGES` dict | `<title>` / `<meta description>` / `<meta keywords>` / robots / canonical / Open Graph / JSON-LD per page |

`<meta keywords>` and `robots` are emitted on every generated page (`keywords`
falls back to `DEFAULT_KEYWORDS`). The `apps.html` `ItemList` and the `blog.html`
`Blog` + `BlogPosting` list JSON-LD are generated from `APPS` and the `blog/*`
`PAGES` entries — add a post the normal way and the blog index picks it up.

`index.html` (the WebGPU canvas homepage) is hand-maintained and NOT generated —
but it is still listed in `sitemap.xml`, so keep `build.py`'s `STATIC_URLS` in sync
if you add hand-made pages.

Inside `parts/content/**` you can write links and asset paths however is convenient
— SPA style (`href="?view=blog/blog_00002.html" data-middle="..."`) or plain
relative (`src="media/x.png"`). The build rewrites them all to **root-relative**
(`href="/blog/blog_00002.html"`, `src="/media/x.png"`), drops `data-middle`, and
also roots `url(...)` in inline styles and `data-src` / `poster` attributes.
Anything already absolute, root-relative, `#anchor`, or `mailto:`/`tel:` is left
alone. There is no `<base>` tag — pages just need to be served from the domain root.

## Build

```bash
python3 build.py
```

Regenerates all pages plus `sitemap.xml`, `robots.txt`, and `CNAME`
(the GitHub Pages custom domain — host taken from `BASE_URL`, skipped for a
`localhost` preview build). Keep `CNAME` in the deployed output or GitHub serves
the site at `<user>.github.io` with no redirect and Google indexes that instead.

Internal links are root-relative and work on any host served from `/`. Only the
absolute URLs — `<link rel="canonical">`, `og:url`, `og:image`, and `sitemap.xml` —
use `https://www.campanilelabs.com`. For a local preview where those also point at
localhost:

```bash
SITE_BASE_URL=http://localhost:4599 python3 build.py
python3 -m http.server 4599
# ...check pages...
python3 build.py            # rebuild for production before deploying
```

## Adding a blog post

1. Add `parts/content/blog/blog_000NN.html` (copy an existing one).
2. Add a `<div class="blog_list_item">` entry to `parts/content/blog.html`.
3. Add a `"blog/blog_000NN.html": dict(...)` entry to `PAGES` in `build.py`
   (title, description, `og_type="article"`, `og_image`, and the BlogPosting JSON-LD).
4. `python3 build.py` and deploy.

## After deploying

- In Google Search Console, submit `https://www.campanilelabs.com/sitemap.xml`.
- Old `main.html?view=...` URLs redirect to `/` (see `main.html`).
