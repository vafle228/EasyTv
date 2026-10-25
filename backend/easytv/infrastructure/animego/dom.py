"""A tiny HTML tree with CSS-like selectors, on the standard library.

Covers exactly what the animego parsers need (tag, .class, #id, [attr], [attr=value] and the descendant
combinator), so the backend doesn't pull in BeautifulSoup for a handful of lookups.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from html.parser import HTMLParser

_VOID = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)


class Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: Node | None = None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Node | str] = []

    # --- attributes

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)

    def __getitem__(self, name: str) -> str:
        return self.attrs[name]

    def has_attr(self, name: str) -> bool:
        return name in self.attrs

    @property
    def classes(self) -> list[str]:
        return (self.attrs.get("class") or "").split()

    # --- navigation

    @property
    def elements(self) -> list[Node]:
        return [c for c in self.children if isinstance(c, Node)]

    def iter(self) -> Iterator[Node]:
        """All descendant elements in document order."""
        for child in self.elements:
            yield child
            yield from child.iter()

    def previous_element(self) -> Node | None:
        if self.parent is None:
            return None
        siblings = self.parent.elements
        i = siblings.index(self)
        return siblings[i - 1] if i > 0 else None

    def first_element(self) -> Node | None:
        return next(iter(self.elements), None)

    def text(self, sep: str = "", strip: bool = True) -> str:
        parts: list[str] = []

        def walk(node: Node) -> None:
            for c in node.children:
                if isinstance(c, str):
                    parts.append(c.strip() if strip else c)
                else:
                    walk(c)

        walk(self)
        return sep.join(p for p in parts if p) if strip else sep.join(parts)

    # --- selectors

    def select(self, selector: str) -> list[Node]:
        steps = [_compile(part) for part in selector.split()]
        found = [n for n in self.iter() if steps[-1](n)]
        if len(steps) == 1:
            return found
        return [n for n in found if _ancestors_match(n, steps[:-1], self)]

    def select_one(self, selector: str) -> Node | None:
        found = self.select(selector)
        return found[0] if found else None


def _ancestors_match(node: Node, steps: list, root: Node) -> bool:
    i = len(steps) - 1
    cur = node.parent
    while cur is not None and cur is not root and i >= 0:
        if steps[i](cur):
            i -= 1
        cur = cur.parent
    return i < 0


_SIMPLE = re.compile(r"""([a-zA-Z][\w-]*)|\.([\w-]+)|#([\w-]+)|\[([\w-]+)(?:=(?:"([^"]*)"|'([^']*)'|([^\]]*)))?\]""")


def _compile(part: str):
    tag: str | None = None
    classes: list[str] = []
    ids: list[str] = []
    attrs: list[tuple[str, str | None]] = []
    pos = 0
    for m in _SIMPLE.finditer(part):
        if m.start() != pos:
            raise ValueError(f"unsupported selector: {part!r}")
        pos = m.end()
        if m.group(1):
            tag = m.group(1).lower()
        elif m.group(2):
            classes.append(m.group(2))
        elif m.group(3):
            ids.append(m.group(3))
        else:
            value = next((g for g in m.group(5, 6, 7) if g is not None), None)
            attrs.append((m.group(4), value))
    if pos != len(part):
        raise ValueError(f"unsupported selector: {part!r}")

    def match(n: Node) -> bool:
        if tag and n.tag != tag:
            return False
        if classes and not set(classes) <= set(n.classes):
            return False
        if ids and n.attrs.get("id") not in ids:
            return False
        for name, value in attrs:
            if name not in n.attrs or (value is not None and n.attrs[name] != value):
                return False
        return True

    return match


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {k: v if v is not None else "" for k, v in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {k: v if v is not None else "" for k, v in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return  # an unmatched end tag is ignored, like browsers do

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def parse_html(html: str) -> Node:
    builder = _Builder()
    builder.feed(html)
    builder.close()
    return builder.root
