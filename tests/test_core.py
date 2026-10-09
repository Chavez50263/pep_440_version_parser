import unittest

from pep_440_version_parser import Version, InvalidVersionError


class TestParsing(unittest.TestCase):

    def test_simple_release(self):
        v = Version("1.0")
        self.assertEqual(v.release, (1, 0))
        self.assertFalse(v.is_prerelease)
        self.assertFalse(v.is_postrelease)
        self.assertEqual(str(v), "1.0")

    def test_release_with_many_segments(self):
        v = Version("1.2.3.4.5")
        self.assertEqual(v.release, (1, 2, 3, 4, 5))

    def test_epoch(self):
        v = Version("1!2.0")
        self.assertEqual(v.epoch, 1)
        self.assertEqual(v.release, (2, 0))
        self.assertEqual(str(v), "1!2.0")

    def test_epoch_zero_omitted(self):
        v = Version("2.0")
        self.assertEqual(v.epoch, 0)
        self.assertNotIn("!", str(v))

    def test_leading_v_prefix(self):
        v = Version("v1.0")
        self.assertEqual(v.release, (1, 0))
        self.assertEqual(str(v), "1.0")

    def test_prerelease_alpha_synonyms(self):
        for text in ["1.0a1", "1.0alpha1", "1.0-a1", "1.0_a1", "1.0.a1"]:
            v = Version(text)
            self.assertEqual(v.pre, ("a", 1))
            self.assertTrue(v.is_prerelease)
            self.assertEqual(str(v), "1.0a1")

    def test_prerelease_c_normalizes_to_rc(self):
        v = Version("1.0c1")
        self.assertEqual(v.pre, ("rc", 1))
        self.assertEqual(str(v), "1.0rc1")

    def test_prerelease_preview_synonym(self):
        v = Version("1.0preview1")
        self.assertEqual(v.pre, ("rc", 1))

    def test_prerelease_no_number_defaults_to_zero(self):
        v = Version("1.0a")
        self.assertEqual(v.pre, ("a", 0))
        self.assertEqual(str(v), "1.0a0")

    def test_postrelease_implicit_dash(self):
        v = Version("1.0-1")
        self.assertEqual(v.post, 1)
        self.assertTrue(v.is_postrelease)
        self.assertEqual(str(v), "1.0.post1")

    def test_postrelease_explicit_label(self):
        for text in ["1.0.post1", "1.0-post-1", "1.0.post.1", "1.0rev1", "1.0r1"]:
            v = Version(text)
            self.assertEqual(v.post, 1)
            self.assertEqual(str(v), "1.0.post1")

    def test_postrelease_no_number_defaults_to_zero(self):
        v = Version("1.0.post")
        self.assertEqual(v.post, 0)
        self.assertEqual(str(v), "1.0.post0")

    def test_dev_release(self):
        for text in ["1.0.dev1", "1.0-dev-1", "1.0.dev.1"]:
            v = Version(text)
            self.assertEqual(v.dev, 1)
            self.assertTrue(v.is_prerelease)
            self.assertEqual(str(v), "1.0.dev1")

    def test_dev_release_no_number_defaults_to_zero(self):
        v = Version("1.0.dev")
        self.assertEqual(v.dev, 0)
        self.assertEqual(str(v), "1.0.dev0")

    def test_local_version(self):
        for text in ["1.0+abc.7", "1.0+abc_7", "1.0+abc-7"]:
            v = Version(text)
            self.assertEqual(v.local, ("abc", "7"))
            self.assertEqual(str(v), "1.0+abc.7")

    def test_local_version_numeric_segments(self):
        v = Version("1.0+123.456")
        self.assertEqual(v.local, ("123", "456"))


class TestComparison(unittest.TestCase):

    def test_release_ordering(self):
        self.assertLess(Version("1.0"), Version("1.1"))
        self.assertLess(Version("1.0"), Version("2.0"))
        self.assertLess(Version("1.0.0"), Version("1.0.1"))

    def test_release_trailing_zeros_compare_equal(self):
        self.assertEqual(Version("1.0"), Version("1.0.0"))
        self.assertEqual(Version("1.0.0.0"), Version("1.0"))

    def test_epoch_dominates(self):
        self.assertLess(Version("1!0.0"), Version("999999!0.0"))
        self.assertLess(Version("1!0.0"), Version("2!0.0"))
        self.assertGreater(Version("1!1.0"), Version("0!9.9"))

    def test_prerelease_before_release(self):
        self.assertLess(Version("1.0a1"), Version("1.0"))
        self.assertLess(Version("1.0rc1"), Version("1.0"))

    def test_prerelease_order(self):
        self.assertLess(Version("1.0a1"), Version("1.0b1"))
        self.assertLess(Version("1.0b1"), Version("1.0rc1"))
        self.assertLess(Version("1.0rc1"), Version("1.0"))

    def test_dev_before_release(self):
        self.assertLess(Version("1.0.dev1"), Version("1.0"))
        self.assertLess(Version("1.0.dev0"), Version("1.0"))

    def test_dev_before_prerelease(self):
        self.assertLess(Version("1.0.dev1"), Version("1.0a1"))

    def test_post_after_release(self):
        self.assertGreater(Version("1.0.post1"), Version("1.0"))
        self.assertLess(Version("1.0.post1"), Version("1.1"))

    def test_combined_dev_and_post(self):
        self.assertLess(Version("1.0.post1.dev1"), Version("1.0.post1"))
        self.assertGreater(Version("1.0.post1.dev1"), Version("1.0"))

    def test_local_sorts_above_base(self):
        self.assertGreater(Version("1.0+abc"), Version("1.0"))
        self.assertGreater(Version("1.0+1"), Version("1.0"))

    def test_local_numeric_above_alpha(self):
        # PEP 440: numeric local segments sort above alphabetic ones.
        self.assertGreater(Version("1.0+1"), Version("1.0+abc"))

    def test_equality_after_normalization(self):
        self.assertEqual(Version("1.0-alpha1"), Version("1.0a1"))
        self.assertEqual(Version("1.0-1"), Version("1.0.post1"))
        self.assertEqual(Version("v1.0"), Version("1.0"))

    def test_sort_list(self):
        versions = [
            Version("1.0.post1"),
            Version("1.0.dev1"),
            Version("1.0a1"),
            Version("1.0"),
            Version("1.0.post1.dev1"),
            Version("2.0"),
        ]
        ordered = sorted(versions)
        expected = [
            "1.0.dev1",
            "1.0a1",
            "1.0",
            "1.0.post1.dev1",
            "1.0.post1",
            "2.0",
        ]
        self.assertEqual([str(v) for v in ordered], expected)

    def test_hash_equal(self):
        self.assertEqual(hash(Version("1.0a1")), hash(Version("1.0-alpha-1")))


class TestRepr(unittest.TestCase):

    def test_repr_roundtrip(self):
        v = Version("1.0a1.post2.dev3+local.4")
        self.assertEqual(repr(v), "Version('1.0a1.post2.dev3+local.4')")


class TestInvalid(unittest.TestCase):

    def test_empty_string(self):
        with self.assertRaises(InvalidVersionError):
            Version("")

    def test_no_release(self):
        with self.assertRaises(InvalidVersionError):
            Version("a1")

    def test_double_dot(self):
        with self.assertRaises(InvalidVersionError):
            Version("1..0")

    def test_trailing_dot(self):
        with self.assertRaises(InvalidVersionError):
            Version("1.0.")

    def test_just_epoch(self):
        with self.assertRaises(InvalidVersionError):
            Version("1!")

    def test_missing_post_number_with_text(self):
        # '1.0post' is valid and means post0; '1.0postX' is not.
        with self.assertRaises(InvalidVersionError):
            Version("1.0postX")


if __name__ == "__main__":
    unittest.main()
