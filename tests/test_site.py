"""Check published metadata, discovery links, and generated content without a browser."""

import contextlib
import io
import json
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from scripts.build_site import ROOT, ProfileParser, build

SITE = ROOT / "static"
ORIGIN = "https://slfdstrctd.github.io/"


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (SITE / "index.html").read_text(encoding="utf-8")
        cls.tags = Elements(cls.html).tags
        cls.meta = {
            attrs.get("name", attrs.get("property")): attrs.get("content")
            for tag, attrs in cls.tags if tag == "meta"
        }
        cls.graph = json.loads(re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            cls.html, re.S,
        )[1])["@graph"]

    def test_search_metadata_and_indexability(self):
        title = re.search(r"<title>(.*?)</title>", self.html)[1]
        self.assertIn("Artem Ponomarenko", title)
        self.assertIn("Analytics Engineer", title)
        self.assertIn("Berlin", title)
        self.assertIn("index", self.meta["robots"].split(", "))
        self.assertNotIn("noindex", self.meta["robots"])
        self.assertEqual(sum(tag == "h1" for tag, _ in self.tags), 1)
        for key in ("og:description", "twitter:description"):
            self.assertEqual(self.meta[key], self.meta["description"])
        self.assertEqual(self.meta["og:url"], ORIGIN)

    def test_structured_profile_identity_and_references(self):
        entities = {item["@id"]: item for item in self.graph}
        profile = next(item for item in self.graph if item["@type"] == "ProfilePage")
        person = entities[profile["mainEntity"]["@id"]]
        self.assertEqual(person["@type"], "Person")
        self.assertIn(person["name"], self.html)
        self.assertIn(person["jobTitle"], self.html)
        self.assertIn(person["worksFor"]["url"], self.html)
        self.assertIn(person["address"]["addressLocality"], self.html)
        for url in person["sameAs"]:
            self.assertIn(f'href="{url}"', self.html)
        self.assertEqual(profile["description"], self.meta["description"])
        for item in self.graph:
            for value in item.values():
                if isinstance(value, dict) and "@id" in value:
                    self.assertIn(value["@id"], entities)

    def test_discovery_and_assets_resolve_inside_deployment(self):
        links = [attrs for tag, attrs in self.tags if tag == "link"]
        self.assertEqual(next(x["href"] for x in links if x["rel"] == "canonical"), ORIGIN)
        self.assertEqual(next(x["href"] for x in links if x["rel"] == "alternate"), ORIGIN + "index.md")
        self.assertEqual(next(x["href"] for x in links if x["rel"] == "describedby"), ORIGIN + "llms.txt")
        urls = [x["href"] for x in links]
        urls.extend(self.meta[key] for key in ("og:image", "twitter:image"))
        for url in urls:
            parsed = urlsplit(url)
            if parsed.netloc and parsed.netloc != urlsplit(ORIGIN).netloc:
                continue
            path = SITE / (parsed.path.lstrip("/") or "index.html")
            self.assertTrue(path.is_file(), f"Missing deployed asset: {url}")
        self.assertEqual(self.meta["og:image"], self.meta["twitter:image"])

    def test_robots_sitemap_and_error_page(self):
        from urllib.robotparser import RobotFileParser
        robots = RobotFileParser()
        robots.parse((SITE / "robots.txt").read_text().splitlines())
        for agent in ("Googlebot", "Bingbot", "OAI-SearchBot", "Claude-SearchBot", "PerplexityBot"):
            for path in ("", "index.md", "llms.txt", "css/style.css"):
                self.assertTrue(robots.can_fetch(agent, ORIGIN + path), (agent, path))
        self.assertEqual(robots.site_maps(), [ORIGIN + "sitemap.xml"])
        sitemap = ET.parse(SITE / "sitemap.xml")
        locations = [item.text for item in sitemap.findall(".//{*}loc")]
        self.assertEqual(locations, [ORIGIN])
        error_meta = Elements((SITE / "404.html").read_text()).tags
        self.assertTrue(any(tag == "meta" and attrs.get("name") == "robots"
                            and "noindex" in attrs["content"] for tag, attrs in error_meta))

    def test_generated_profile_preserves_visible_content(self):
        # Generate into an isolated directory, then compare with the deployed copy.
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "index.html").write_text(self.html, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                build(directory)
            for name in ("index.md", "llms.txt"):
                self.assertEqual((directory / name).read_bytes(), (SITE / name).read_bytes())
        markdown = (SITE / "index.md").read_text()
        parser = ProfileParser()
        parser.feed(self.html)
        for paragraph in re.findall(r"<p[^>]*>(.*?)</p>", self.html, re.S):
            self.assertIn(" ".join(paragraph.split()), markdown)
        for text in ("2025 – Present", "2018 – 2022", "## Contact", "mailto:aponomarenko.pro@gmail.com"):
            self.assertIn(text, markdown)
        self.assertNotIn("@context", markdown)

    def test_converter_excludes_scripts_and_resolves_links(self):
        parser = ProfileParser()
        parser.feed('<link rel="canonical" href="https://example.com/">'
                    '<body><h1>Name</h1><script>private()</script>'
                    '<p>Hello <a href="/about">there</a>.</p></body>')
        self.assertEqual(parser.blocks, ["# Name", "Hello [there](https://example.com/about)."])


if __name__ == "__main__":
    unittest.main()
