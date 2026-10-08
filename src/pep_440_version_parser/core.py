import re


class InvalidVersionError(ValueError):
    """Raised when a string does not conform to PEP 440."""


# The canonical PEP 440 regular expression, as documented in the specification.
# Group names match the conceptual segments so the parser can read them directly.
# Intentionally not relaxed: rejecting strings like '1.0-' here means downstream
# code never has to second-guess what 'partial' input it received.
_VERSION_PATTERN = r"""
    ^
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?
        (?P<release>[0-9]+(?:\.[0-9]+)*)
        (?P<pre>
            [-_.]?
            (?P<pre_l>alpha|a|beta|b|c|rc|preview|pre)
            [-_.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_.]?
                (?P<post_l>post|rev|r)
                [-_.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>
            [-_.]?
            (?P<dev_l>dev)
            [-_.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?
    $
"""

_VERSION_RE = re.compile(_VERSION_PATTERN, re.VERBOSE | re.IGNORECASE)

_PRE_NORMALIZE = {
    "alpha": "a",
    "a": "a",
    "beta": "b",
    "b": "b",
    "c": "rc",
    "rc": "rc",
    "pre": "rc",
    "preview": "rc",
}

_POST_NORMALIZE = {
    "post": "post",
    "rev": "post",
    "r": "post",
}


class Version:
    """A parsed PEP 440 version.

    Supports epochs, release segments, pre/post/dev releases, and local versions.
    Normalizes the canonical string form (e.g. '1.0-alpha1' -> '1.0a1') so that
    two equivalent versions compare equal.
    """

    __slots__ = (
        "epoch",
        "release",
        "pre",
        "post",
        "dev",
        "local",
        "_key",
        "_str",
    )

    def __init__(self, version):
        match = _VERSION_RE.match(version if isinstance(version, str) else str(version))
        if match is None:
            raise InvalidVersionError(f"{version!r} is not a valid PEP 440 version")

        g = match.groupdict()

        self.epoch = int(g["epoch"]) if g["epoch"] else 0

        # Stored as a tuple to make later comparisons straightforward.
        self.release = tuple(int(x) for x in g["release"].split("."))

        if g["pre"]:
            label = _PRE_NORMALIZE[g["pre_l"].lower()]
            num = int(g["pre_n"]) if g["pre_n"] is not None else 0
            self.pre = (label, num)
        else:
            self.pre = None

        if g["post"]:
            if g["post_n1"] is not None:
                num = int(g["post_n1"])
            else:
                num = int(g["post_n2"]) if g["post_n2"] is not None else 0
            self.post = num
        else:
            self.post = None

        if g["dev"]:
            num = int(g["dev_n"]) if g["dev_n"] is not None else 0
            self.dev = num
        else:
            self.dev = None

        # Local segments preserved verbatim (split into components) for string
        # reconstruction and numeric-aware comparison.
        if g["local"]:
            self.local = tuple(g["local"].replace("_", ".").replace("-", ".").split("."))
        else:
            self.local = None

        self._key = self._build_key()
        self._str = self._build_str()

    @property
    def is_prerelease(self):
        """True when the version is a pre-release or a dev release."""
        return self.pre is not None or self.dev is not None

    @property
    def is_postrelease(self):
        """True when the version is a post-release."""
        return self.post is not None

    def _build_key(self):
        # Comparison follows PEP 440 ordering. Dev releases sort before the
        # release; pre-releases sort between dev and the release; post-releases
        # sort after the release. Local versions sort above their non-local base.
        epoch = self.epoch

        release = list(self.release)
        while release and release[-1] == 0:
            release.pop()
        release = tuple(release)

        if self.pre is None and self.dev is not None and self.post is None:
            # N.dev sorts just below N. Represent with a sentinel pre.
            pre = ("", -1)
        elif self.pre is None:
            # A plain release, or a post-release of a plain release, sorts above
            # any pre-release of the same release. Use a sentinel label that
            # sorts after 'a', 'b', 'rc'.
            pre = ("~", 0)
        else:
            pre = self.pre

        if self.dev is None:
            dev = float("inf")
        else:
            dev = self.dev

        if self.post is None:
            post = float("-inf")
        else:
            post = self.post

        if self.local is None:
            local = ()
        else:
            local = []
            for seg in self.local:
                if seg.isdigit():
                    local.append((1, int(seg)))
                else:
                    local.append((-1, seg))
            local = tuple(local)

        return (epoch, release, pre, post, dev, local)

    def _build_str(self):
        parts = []
        if self.epoch:
            parts.append(f"{self.epoch}!")
        parts.append(".".join(str(x) for x in self.release))
        if self.pre is not None:
            parts.append(f"{self.pre[0]}{self.pre[1]}")
        if self.post is not None:
            parts.append(f".post{self.post}")
        if self.dev is not None:
            parts.append(f".dev{self.dev}")
        if self.local:
            parts.append("+" + ".".join(self.local))
        return "".join(parts)

    def __str__(self):
        return self._str

    def __repr__(self):
        return f"Version('{self._str}')"

    def __eq__(self, other):
        if isinstance(other, Version):
            return self._key == other._key
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other):
        if isinstance(other, Version):
            return self._key < other._key
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Version):
            return self._key <= other._key
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Version):
            return self._key > other._key
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Version):
            return self._key >= other._key
        return NotImplemented

    def __hash__(self):
        return hash(self._key)
