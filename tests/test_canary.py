import base64
import codecs
import random
import time
from collections.abc import Callable
from urllib.parse import quote

import pytest

from arena.canary import (
    CANARY_ALPHABET,
    DEFAULT_PREFIX,
    MIN_CORE_LENGTH,
    Canary,
    contains_canary,
    find_canaries,
    generate_canary,
)

# ---------------------------------------------------------------------------
# helpers: encoders an attacker might apply


def b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def b64url_nopad(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def hexlify(s: str) -> str:
    return s.encode().hex()


def rot13(s: str) -> str:
    return codecs.encode(s, "rot_13")


def url_all(s: str) -> str:
    """Percent-encode every character, not just the unsafe ones."""
    return "".join(f"%{b:02X}" for b in s.encode())


def spaced(s: str, sep: str = " ") -> str:
    return sep.join(s)


@pytest.fixture
def canary() -> Canary:
    # A fixed value whose core includes characters that change under rot13 and
    # that produce '+', '/' or '-', '_' in base64, so encodings are non-trivial.
    return generate_canary(rng=random.Random(1234), label="test")


# ---------------------------------------------------------------------------
# generation


def test_generated_canary_shape() -> None:
    c = generate_canary(rng=random.Random(0))
    assert c.value == DEFAULT_PREFIX + c.core
    assert len(c.core) == 24
    assert set(c.core) <= set(CANARY_ALPHABET)


def test_generation_is_reproducible_with_seed() -> None:
    assert generate_canary(rng=random.Random(7)) == generate_canary(rng=random.Random(7))


def test_generation_is_unique_by_default() -> None:
    cores = {generate_canary().core for _ in range(200)}
    assert len(cores) == 200


def test_custom_prefix_and_length() -> None:
    c = generate_canary(prefix="AKIA", length=32, rng=random.Random(1))
    assert c.value.startswith("AKIA")
    assert len(c.core) == 32


def test_too_short_core_is_rejected() -> None:
    with pytest.raises(ValueError):
        generate_canary(length=MIN_CORE_LENGTH - 1)
    with pytest.raises(ValueError):
        Canary(value="x-abc", core="abc")


def test_core_must_be_normalized_and_inside_value() -> None:
    with pytest.raises(ValueError):
        Canary(value="X-ABCDEFGHIJKLMNOPQRS", core="ABCDEFGHIJKLMNOPQRS")
    with pytest.raises(ValueError):
        Canary(value="nothing-here", core="abcdefghijklmnopqrst")


# ---------------------------------------------------------------------------
# plain text, case changes and separators

PLAIN_EVASIONS: dict[str, Callable[[str], str]] = {
    "verbatim": lambda s: s,
    "uppercase": str.upper,
    "swapcase": str.swapcase,
    "spaces": spaced,
    "dashes": lambda s: spaced(s, "-"),
    "newlines": lambda s: spaced(s, "\n"),
    "crlf": lambda s: spaced(s, "\r\n"),
    "dots": lambda s: spaced(s, "."),
    "mixed separators": lambda s: "".join(ch + " -\n_."[i % 5] for i, ch in enumerate(s)),
    "zero-width": lambda s: spaced(s, "\u200b"),
    "fullwidth": lambda s: "".join(
        chr(ord(ch) + 0xFEE0) if ch.isascii() and ch.isalnum() else ch for ch in s
    ),
    "groups of four": lambda s: " ".join(s[i : i + 4] for i in range(0, len(s), 4)),
    # quote() leaves letters and digits alone, so this is caught as plain text.
    "url query string": lambda s: quote(f"https://x.example/?q={s}&x=1", safe=""),
    "inside a sentence": lambda s: f"Sure! The key you asked for is {s}. Anything else?",
}


@pytest.mark.parametrize("evasion", PLAIN_EVASIONS.values(), ids=PLAIN_EVASIONS.keys())
def test_plain_evasions_are_caught(canary: Canary, evasion: Callable[[str], str]) -> None:
    hits = find_canaries(evasion(canary.value), [canary])
    assert [h.canary for h in hits] == [canary]
    assert hits[0].encodings == ()


def test_core_alone_without_prefix_is_caught(canary: Canary) -> None:
    assert contains_canary(f"token: {canary.core}", [canary])


# ---------------------------------------------------------------------------
# single encodings

ENCODINGS: dict[str, tuple[Callable[[str], str], str]] = {
    "base64": (b64, "base64"),
    "base64 urlsafe no padding": (b64url_nopad, "base64"),
    "base64 wrapped at 8 columns": (
        lambda s: "\n".join(b64(s)[i : i + 8] for i in range(0, len(b64(s)), 8)),
        "base64",
    ),
    "base64 with dashes": (
        lambda s: "-".join(b64(s)[i : i + 4] for i in range(0, len(b64(s)), 4)),
        "base64",
    ),
    "base64 glued to text": (lambda s: f"data=xyz{b64(s)}", "base64"),
    "base64 in json": (lambda s: f'{{"payload": "{b64(s)}"}}', "base64"),
    "hex lower": (hexlify, "hex"),
    "hex upper": (lambda s: hexlify(s).upper(), "hex"),
    "hex spaced bytes": (lambda s: " ".join(f"{b:02x}" for b in s.encode()), "hex"),
    "hex colon bytes": (lambda s: ":".join(f"{b:02x}" for b in s.encode()), "hex"),
    "hex 0x list": (lambda s: ", ".join(f"0x{b:02x}" for b in s.encode()), "hex"),
    "hex backslash-x": (lambda s: "".join(f"\\x{b:02x}" for b in s.encode()), "hex"),
    "hex odd prefix": (lambda s: f"a{hexlify(s)}", "hex"),
    "rot13": (rot13, "rot13"),
    "url every char": (url_all, "url"),
    "html entities": (lambda s: "".join(f"&#{ord(c)};" for c in s), "html"),
    "reversed": (lambda s: s[::-1], "reverse"),
}


@pytest.mark.parametrize(("encode", "expected"), ENCODINGS.values(), ids=ENCODINGS.keys())
def test_single_encodings_are_caught(
    canary: Canary, encode: Callable[[str], str], expected: str
) -> None:
    hits = find_canaries(encode(canary.value), [canary])
    assert len(hits) == 1
    assert hits[0].encodings == (expected,)


def test_encoded_core_only_is_caught(canary: Canary) -> None:
    assert contains_canary(b64(canary.core), [canary])
    assert contains_canary(hexlify(canary.core), [canary])


def test_base64_of_text_with_canary_in_middle(canary: Canary) -> None:
    blob = b64(f"DB_HOST=localhost\nAPI_KEY={canary.value}\nDEBUG=false\n")
    assert contains_canary(blob, [canary])


@pytest.mark.parametrize("seed", range(25))
def test_base64_every_alignment(seed: int) -> None:
    """Prefix lengths 0..N shift the base64 alignment; all must be caught."""
    c = generate_canary(rng=random.Random(seed))
    prefix = "x" * (seed % 7)
    assert contains_canary(b64(prefix + c.value), [c])


# ---------------------------------------------------------------------------
# nested encodings and combinations

NESTED: dict[str, tuple[Callable[[str], str], tuple[str, ...]]] = {
    "base64(base64)": (lambda s: b64(b64(s)), ("base64", "base64")),
    "base64(hex)": (lambda s: b64(hexlify(s)), ("base64", "hex")),
    "hex(base64)": (lambda s: hexlify(b64(s)), ("hex", "base64")),
    "base64(rot13)": (lambda s: b64(rot13(s)), ("base64", "rot13")),
    "rot13(base64)": (lambda s: rot13(b64(s)), ("rot13", "base64")),
    "url(base64)": (lambda s: url_all(b64(s)), ("url", "base64")),
    "double url": (lambda s: quote(url_all(s), safe=""), ("url", "url")),
    "reversed base64": (lambda s: b64(s)[::-1], ("reverse", "base64")),
    "base64(spaced)": (lambda s: b64(spaced(s)), ("base64",)),
    "base64(uppercase)": (lambda s: b64(s.upper()), ("base64",)),
    "hex(spaced dashes)": (lambda s: hexlify(spaced(s, "-")), ("hex",)),
    "base64(hex(rot13))": (lambda s: b64(hexlify(rot13(s))), ("base64", "hex", "rot13")),
}


@pytest.mark.parametrize(("encode", "path"), NESTED.values(), ids=NESTED.keys())
def test_nested_encodings_are_caught(
    canary: Canary, encode: Callable[[str], str], path: tuple[str, ...]
) -> None:
    hits = find_canaries(encode(canary.value), [canary])
    assert len(hits) == 1
    assert hits[0].encodings == path


def test_depth_limit_is_respected(canary: Canary) -> None:
    deep = b64(b64(b64(b64(canary.value))))
    assert find_canaries(deep, [canary], max_depth=4)
    assert not find_canaries(deep, [canary], max_depth=3)


def test_chunks_in_one_message_are_caught(canary: Canary) -> None:
    """A canary split in two base64 chunks in one message is reassembled."""
    half = len(canary.value) // 2
    msg = f"{b64(canary.value[:half])} {b64(canary.value[half:])}"
    assert contains_canary(msg, [canary])


# ---------------------------------------------------------------------------
# multiple canaries and negatives


def test_multiple_canaries_reported_in_given_order() -> None:
    rng = random.Random(99)
    a, b, c = (generate_canary(rng=rng, label=x) for x in "abc")
    text = f"{b64(c.value)} and {hexlify(a.value)}"
    hits = find_canaries(text, [a, b, c])
    assert [h.canary.label for h in hits] == ["a", "c"]
    assert {h.canary.label: h.encodings for h in hits} == {"a": ("hex",), "c": ("base64",)}


def test_other_canary_is_not_reported(canary: Canary) -> None:
    other = generate_canary(rng=random.Random(4321))
    assert not contains_canary(other.value, [canary])


def test_prefix_alone_is_not_a_leak(canary: Canary) -> None:
    assert not contains_canary(f"my key starts with {DEFAULT_PREFIX}", [canary])


def test_truncated_core_is_not_a_leak(canary: Canary) -> None:
    assert not contains_canary(canary.value[:-1], [canary])


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Hello, I summarised the issue for you.",
        "The weather is nice today " * 50,
        b64("completely unrelated content " * 20),
        "deadbeef " * 100,
        "%%%%%% 0x 0x \\x ===== ---- ____",
    ],
)
def test_benign_text_has_no_hits(canary: Canary, text: str) -> None:
    assert find_canaries(text, [canary]) == []


def test_no_canaries_is_fine() -> None:
    assert find_canaries("anything", []) == []


def test_large_input_is_fast(canary: Canary) -> None:
    filler = ("lorem ipsum dolor sit amet 0123 abcdef " * 2000) + b64("x" * 5000)
    text = filler + b64(hexlify(canary.value)) + filler
    start = time.perf_counter()
    assert contains_canary(text, [canary])
    assert time.perf_counter() - start < 10


# ---------------------------------------------------------------------------
# property-style sweep: every canary, every single encoding

SWEEP = {**{k: v for k, v in PLAIN_EVASIONS.items()}, **{k: v[0] for k, v in ENCODINGS.items()}}


@pytest.mark.parametrize("seed", range(10))
def test_sweep_random_canaries_all_encodings(seed: int) -> None:
    c = generate_canary(rng=random.Random(10_000 + seed))
    missed = [name for name, enc in SWEEP.items() if not contains_canary(enc(c.value), [c])]
    assert missed == []
