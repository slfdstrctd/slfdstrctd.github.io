"""Generate agent-readable files from the visible homepage; no dependencies."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]


class ProfileParser(HTMLParser):
    """Extract profile text and links, excluding head metadata and scripts."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.ignored = 0
        self.block = None
        self.parts = []
        self.blocks = []
        self.canonical = None
        self.description = None
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs["href"]
        if tag == "meta" and attrs.get("name") == "description":
            self.description = attrs["content"]
        if tag == "body":
            self.in_body = True
        if not self.in_body:
            return
        if tag in {"script", "style"}:
            self.ignored += 1
        if self.ignored:
            return
        if tag in {"h1", "h2", "h3", "p", "nav"} or (
            tag == "span" and "date" in attrs.get("class", "").split()
        ):
            self.block = tag
            self.parts = []
        if tag == "a" and self.block:
            self.parts.append("[")
            self.link = urljoin(self.canonical, attrs["href"])

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
        if tag in {"script", "style"} and self.ignored:
            self.ignored -= 1
            return
        if self.ignored:
            return
        if tag == "a" and self.link:
            self.parts.append(f"]({self.link})")
            self.link = None
        if tag == self.block:
            text = " ".join("".join(self.parts).split())
            prefix = "#" * int(tag[1]) + " " if tag in {"h1", "h2", "h3"} else ""
            self.blocks.append(prefix + text)
            self.block = None

    def handle_data(self, data):
        if self.in_body and not self.ignored and self.block:
            self.parts.append(data)


def build(directory=ROOT / "static"):
    profile = ProfileParser()
    profile.feed((directory / "index.html").read_text(encoding="utf-8"))
    if not profile.canonical or not profile.description:
        raise ValueError("Homepage must define a canonical URL and description")
    if not profile.blocks or not profile.blocks[0].startswith("# "):
        raise ValueError("Homepage must start with a name heading")

    markdown = "\n\n".join(profile.blocks) + "\n"
    (directory / "index.md").write_text(markdown, encoding="utf-8")
    (directory / "llms.txt").write_text(
        f"{profile.blocks[0]}\n\n> {profile.description}\n\n"
        "## Profile\n\n"
        f"- [Full profile]({urljoin(profile.canonical, 'index.md')}): "
        "Current work, previous experience, education, and contact links. "
        "A Markdown version generated from the visible homepage.\n",
        encoding="utf-8",
    )
    print("Generated index.md and llms.txt from the homepage.")


if __name__ == "__main__":
    build()
