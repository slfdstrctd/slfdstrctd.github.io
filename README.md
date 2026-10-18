# Artem Ponomarenko

A small, static personal homepage hosted on GitHub Pages. The public site is
https://slfdstrctd.github.io/.

## Edit and preview

Edit `static/index.html` and `static/css/style.css`. Then run:

```sh
python3 scripts/build_site.py
python3 -m unittest discover -s tests
python3 -m http.server 8765 --directory static
```

Open http://localhost:8765/. The build uses only Python's standard library.
GitHub Actions regenerates the readable files and runs the checks before deploying
the `static/` directory on pushes to `master`.

## Search and agent discovery

- The canonical homepage has a descriptive title, matching search/share
  descriptions, and linked WebSite, ProfilePage, and Person structured data.
- Keep structured data consistent with visible job, education, and contact details.
- `robots.txt` allows crawling, including search and AI search bots.
- `sitemap.xml` lists only the canonical homepage. There is no hand-maintained
  last-modified date to become inaccurate; add a real content modification date
  only if it can be maintained reliably. The error page is marked `noindex`.
- `index.md` and `llms.txt` are generated from the homepage. Do not edit them by hand.
  HTML link elements advertise the Markdown alternative and the agent overview.
  These files are a convenience for agents, not a ranking guarantee.
- `social-preview.png` is the share image; it is not loaded in the visible page.
  It should remain consistent with the name, job title, and location.

After publishing, verify the site in Google Search Console and Bing Webmaster
Tools, submit `/sitemap.xml`, and inspect/request indexing for the homepage.
Ownership verification requires the site owner's account-specific token. Do not
add placeholder verification tags. Check the live URL in PageSpeed Insights and
Google's Rich Results Test after deployment; local audits do not verify indexing.

GitHub Pages serves static files. It does not let this repository configure DNS
records for the `github.io` domain, custom HTTP Link headers, or content negotiation
at `/` for `Accept: text/markdown`. A static Markdown alternative is available at
`/index.md`, but it does not satisfy a content-negotiation check.

The Cloudflare agent-readiness scanner also checks OAuth, API catalogs, MCP
servers, registered tools, agent authentication, and other service protocols.
This site has no such services. Do not publish fictitious manifests or add
authentication and APIs just to raise that scanner's score. Those checks are
separate from a search engine's ability to read and index a personal homepage.
