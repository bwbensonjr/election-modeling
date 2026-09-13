"""Resolving a race's candidates to OCPF filers.

There is no shared identifier between the election results and OCPF: the race
table names a candidate `"Richard J. Ross"`, OCPF names the filer
`"Ross, Richard J."`. Matching is surname-first inside a district-year, which
is what makes it safe -- a district-year holds one to eight filers, so a
surname is very nearly a key, and the given name is only needed to break a tie.

Fuzzy string distance over the whole filer list was rejected: a wrong match
attributes one campaign's money to a different candidate, which is worse than
no match at all, and edit distance cannot tell two cousins apart (design.md,
D3).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Generational suffixes are not part of a surname. Leaving them in is what made
# a naive matcher read `Harold P. Naughton, Jr.` as surname "jr".
SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v"})

# Courtesy titles occasionally present on one side only.
TITLES = frozenset({"mr", "mrs", "ms", "dr", "rev", "hon"})

# How a match was made, recorded on every candidate row so a result can be
# audited without re-running the resolution.
RULE_SURNAME = "surname"
RULE_SURNAME_GIVEN = "surname+given"
RULE_MULTIWORD_SURNAME = "multiword-surname"
RULE_PARTIAL_SURNAME = "partial-surname+given"
RULE_AMBIGUOUS = "ambiguous"
RULE_UNMATCHED = "unmatched"

MATCHED_RULES = frozenset(
    {RULE_SURNAME, RULE_SURNAME_GIVEN, RULE_MULTIWORD_SURNAME, RULE_PARTIAL_SURNAME}
)


def _words(text: str) -> list[str]:
    """Lowercase ASCII words, with punctuation, titles and suffixes removed."""
    folded = unicodedata.normalize("NFKD", str(text))
    folded = folded.encode("ascii", "ignore").decode()
    parts = re.sub(r"[^A-Za-z ]", " ", folded).lower().split()
    return [w for w in parts if w not in SUFFIXES and w not in TITLES]


@dataclass(frozen=True)
class Name:
    """A name reduced to the pieces matching actually compares."""

    surname: str
    given: str
    # Trailing word groups, longest first, so a two-word surname can be tried
    # before the single last word.
    surname_options: tuple[str, ...]
    raw: str

    @property
    def is_empty(self) -> bool:
        return not self.surname


def parse_filer(name: str) -> Name:
    """Parse OCPF's `"Surname, Given M."` form."""
    parts = str(name).split(",", 1)
    # A suffix after the comma (`"Smith, Jr"`) leaves no given name; _words
    # drops it, so the given side can legitimately be empty.
    surname_words = _words(parts[0])
    given_words = _words(parts[1]) if len(parts) > 1 else []
    surname = " ".join(surname_words)
    options = tuple(
        " ".join(surname_words[i:]) for i in range(len(surname_words))
    ) or ("",)
    return Name(
        surname=surname,
        given=given_words[0] if given_words else "",
        surname_options=options,
        raw=str(name),
    )


def parse_candidate(name: str) -> Name:
    """Parse the race table's `"Given M. Surname"` form.

    The surname may be more than one word (`Griffin Dunne`, `Van Tassell`), and
    which words belong to it cannot be known from this side alone, so every
    trailing group is offered and the filer list decides.
    """
    words = _words(name)
    if not words:
        return Name("", "", ("",), str(name))
    # Longest trailing groups first: "griffin dunne" before "dunne".
    options = tuple(" ".join(words[i:]) for i in range(1, len(words)))
    return Name(
        surname=words[-1],
        given=words[0],
        surname_options=options or (words[-1],),
        raw=str(name),
    )


def _given_agrees(candidate: Name, filer: Name) -> bool:
    """Whether two given names can be the same person.

    A diminutive is a prefix of the formal name about as often as not
    (`Bob`/`Robert` is neither), so agreement is: equal, one a prefix of the
    other, or a shared first letter. This is deliberately loose -- it is only
    ever used to break a tie among filers who already share a surname in the
    same district-year.
    """
    a, b = candidate.given, filer.given
    if not a or not b:
        return True
    if a == b or a.startswith(b) or b.startswith(a):
        return True
    return a[0] == b[0]


@dataclass(frozen=True)
class Match:
    """The outcome of resolving one candidate against a district-year roster."""

    cpf_id: object | None
    filer_name: str
    rule: str
    considered: int

    @property
    def matched(self) -> bool:
        return self.rule in MATCHED_RULES


def match_candidate(candidate_name: str, roster: list[dict]) -> Match:
    """Resolve one candidate against the filers of a district-year.

    Returns an unmatched or ambiguous result rather than guessing: an ambiguous
    match is recorded as such and resolved to neither filer (campaign-finance
    spec, "An ambiguous match is not guessed").
    """
    candidate = parse_candidate(candidate_name)
    considered = len(roster)
    if candidate.is_empty or not roster:
        return Match(None, "", RULE_UNMATCHED, considered)

    parsed = [(row, parse_filer(row.get("filer_name", ""))) for row in roster]

    # Longest surname group first, so `griffin dunne` is preferred to `dunne`.
    for option in sorted(set(candidate.surname_options), key=len, reverse=True):
        if not option:
            continue
        hits = [(row, filer) for row, filer in parsed if option in filer.surname_options]
        if not hits:
            continue
        multiword = " " in option
        if len(hits) == 1:
            row, filer = hits[0]
            rule = RULE_MULTIWORD_SURNAME if multiword else RULE_SURNAME
            return Match(row.get("cpf_id"), filer.raw, rule, considered)
        narrowed = [(row, filer) for row, filer in hits if _given_agrees(candidate, filer)]
        if len(narrowed) == 1:
            row, filer = narrowed[0]
            return Match(row.get("cpf_id"), filer.raw, RULE_SURNAME_GIVEN, considered)
        return Match(None, "", RULE_AMBIGUOUS, considered)

    # A candidate carrying two surnames -- a maiden and a married name --
    # where OCPF records only one of them. `Susannah M. Whipps Lee` is
    # `Whipps, Susannah M.` there, and "whipps" is a middle word, so no
    # trailing group reaches it. Tried last, restricted to the district-year's
    # handful of filers, and requiring the given name to agree, because on its
    # own "any word matches any surname" would be far too loose.
    words = [w for w in _words(candidate_name)[1:]]
    for word in words:
        hits = [
            (row, filer)
            for row, filer in parsed
            if word in filer.surname_options and _given_agrees(candidate, filer)
        ]
        if len(hits) == 1:
            row, filer = hits[0]
            return Match(row.get("cpf_id"), filer.raw, RULE_PARTIAL_SURNAME, considered)

    return Match(None, "", RULE_UNMATCHED, considered)


def surnames(candidate_name: str) -> set:
    """Every trailing word group a candidate's surname might be.

    Used to find which district a retired seat's race belongs to, by looking
    for the candidates rather than the district name.
    """
    return {o for o in parse_candidate(candidate_name).surname_options if o}
