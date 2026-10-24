"""Query expansion for retrieval, never for the prompt.

An employee asks in their own words; the corpus uses the words HR wrote. A lexical or embedding
index can miss an answer that is present when the question and the document use different nouns for
the same thing (``презенты`` vs ``деловой подарок``). The expansion below appends the document
vocabulary to the *search* query only. The original question still goes to the model, so the answer
is grounded in the retrieved fragments and the user's wording is preserved.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-zа-яё0-9]+")

# Each rule is a predicate over the tokenized question and the extra vocabulary to search with.
# Keep additions concrete: a broad synonym list turns one question into a corpus-wide match.
_GIFT_WORDS = frozenset(
    {
        "презент",
        "презента",
        "презенты",
        "презентов",
        "презентом",
        "презентами",
        "презенте",
        "презентик",
    }
)
_SOUVENIR_WORDS = frozenset(
    {"сувенир", "сувениры", "сувениров", "сувениром", "сувенирами", "сувенире"}
)
_MENTOR_WORDS = frozenset(
    {
        "наставник",
        "наставника",
        "наставнику",
        "наставником",
        "наставнике",
        "наставники",
        "наставников",
        "наставниками",
        "куратор",
        "куратора",
        "куратору",
        "куратором",
        "кураторе",
    }
)

_EXPANSIONS: tuple[tuple[frozenset[str], str], ...] = (
    (
        _GIFT_WORDS,
        "подарок подарки корпоративные подарки деловой подарок представительские расходы",
    ),
    (_SOUVENIR_WORDS, "подарок подарки сувенир"),
    (_MENTOR_WORDS, "наставничество адаптация испытательный срок"),
)


def expand_query(text: str) -> str:
    """Return the original query plus vocabulary that the corpus is likely to contain.

    The function is intentionally monotonic: it never removes or rewrites user words, so an audit
    can compare the original question with the search text and explain every addition.
    """
    words = frozenset(_WORD.findall(text.casefold()))
    additions = tuple(
        expansion for triggers, expansion in _EXPANSIONS if words & triggers
    )
    if not additions:
        return text
    return f"{text} {' '.join(dict.fromkeys(additions))}"
