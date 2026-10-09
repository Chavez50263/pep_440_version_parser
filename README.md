# PEP 440 Version Parser

Parses PEP 440 version strings (epochs, pre/post/dev releases, local segments) with zero third-party dependencies.

```python
from pep_440_version_parser import Version, InvalidVersionError

v = Version("1!2.3a4.post5.dev6+ubuntu.7")
print(v.epoch)            # 1
print(v.release)          # (2, 3)
print(v.pre)              # ('a', 4)
print(v.post)             # 5
print(v.dev)              # 6
print(v.local)            # ('ubuntu', '7')
print(v.is_prerelease)    # True
print(str(v))             # 1!2.3a4.post5.dev6+ubuntu.7

Version("1.0a1") < Version("1.0")    # True
Version("1.0") == Version("1.0.0")   # True
```

## Why this exists

The standard library does not parse PEP 440. `packaging` does, but it is a third-party dependency you may not be able to add. This library is a single self-contained module that implements the spec's parse/normalize/order rules faithfully enough for the common cases — including epochs, the pre/post/dev/local segments, and canonical string normalization — without pulling in anything outside `re`.

The trade-off: there is no public version-specifier matcher (`>=`, `~=`, etc.). This parses and orders versions; it does not resolve requirement strings.

## Edge you will hit

The comparison key treats `1.0.dev0` as sorting below `1.0a0`, which is the order PEP 440 mandates. If you expect dev releases to sort adjacent to the final release, this will surprise you — the spec places them strictly below every pre-release of the same version.
