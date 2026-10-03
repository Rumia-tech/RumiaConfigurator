"""The developer guide stays in step with the code (NFR-MNT-04).

Every Python module is cited in the guide with its path from the repository
root, and every link between guide pages points to an existing page and
heading. The public wiki is generated from these files, so broken links would
break it too.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "development"
DOCUMENTED_DIRS = ("src", "scripts", "packaging")

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def pages() -> list[Path]:
    return sorted(GUIDE.glob("*.md"))


def guide_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in pages())


def modules() -> list[str]:
    found = []
    for folder in DOCUMENTED_DIRS:
        for path in (ROOT / folder).rglob("*.py"):
            if path.name != "__init__.py" and "__pycache__" not in path.parts:
                found.append(path.relative_to(ROOT).as_posix())
    return sorted(found)


def slug(heading: str) -> str:
    """Anchor GitHub gives to a heading."""
    text = heading.strip().lower().replace("`", "")
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(page: Path) -> set[str]:
    text = FENCE.sub("", page.read_text(encoding="utf-8"))
    return {slug(h) for h in HEADING.findall(text)}


def test_guide_exists_with_an_index() -> None:
    assert (GUIDE / "README.md").is_file()
    assert len(pages()) > 1


@pytest.mark.parametrize("module", modules())
def test_every_module_is_documented(module: str) -> None:
    assert f"`{module}`" in guide_text(), (
        f"{module} is not cited in docs/development/: describe it and write its path "
        "from the repository root in backticks."
    )


@pytest.mark.parametrize("page", pages(), ids=lambda p: p.name)
def test_internal_links_work(page: Path) -> None:
    text = FENCE.sub("", page.read_text(encoding="utf-8"))
    broken = []
    for target in LINK.findall(text):
        if re.match(r"^[a-z]+:", target):  # http:, https:, mailto:
            continue
        file_part, _, anchor = target.partition("#")
        linked = page if not file_part else GUIDE / file_part
        if not linked.is_file() or linked.parent != GUIDE:
            broken.append(f"{target}: no page {file_part} in docs/development/")
        elif anchor and anchor not in anchors(linked):
            broken.append(f"{target}: no heading with anchor #{anchor} in {linked.name}")
    assert broken == []


def test_every_page_has_a_unique_title() -> None:
    """The first line ``# Title`` names the page in the wiki."""
    titles = []
    for page in pages():
        first = page.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("# "), f"{page.name} must start with a '# Title' line"
        titles.append(first[2:].strip())
    assert len(titles) == len(set(titles)), titles


def test_guide_pages_are_linked_from_the_index() -> None:
    index = (GUIDE / "README.md").read_text(encoding="utf-8")
    missing = [p.name for p in pages() if p.name != "README.md" and f"({p.name})" not in index]
    assert missing == []
