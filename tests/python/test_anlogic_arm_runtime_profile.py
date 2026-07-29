import importlib.util
import json
import pathlib
import tempfile
import unittest


REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = REPOSITORY / "scripts/vendor/validate_anlogic_arm_runtime_profile.py"
SPEC = importlib.util.spec_from_file_location("runtime_profile_validator", MODULE_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)


class RuntimeProfileTest(unittest.TestCase):
    def load(self, name):
        return VALIDATOR.load_json(VALIDATOR.PROFILE_PATHS[name])

    def test_frozen_profiles_pass(self):
        for name in VALIDATOR.PROFILE_PATHS:
            VALIDATOR.validate_profile(self.load(name), name)

    def test_openmp_off_dual_profile_is_rejected(self):
        profile = self.load("recommended-dual-thread")
        profile["build_identity"]["NCNN_OPENMP"] = False
        with self.assertRaisesRegex(VALIDATOR.ProfileError, "NCNN_OPENMP"):
            VALIDATOR.validate_profile(profile, "recommended-dual-thread")

    def test_wrong_thread_count_is_rejected(self):
        profile = self.load("recommended-dual-thread")
        profile["runtime"]["configured_threads"] = 1
        with self.assertRaisesRegex(VALIDATOR.ProfileError, "runtime.threads"):
            VALIDATOR.validate_profile(profile, "recommended-dual-thread")

    def test_wrong_ncnn_identity_is_rejected(self):
        profile = self.load("recommended-dual-thread")
        profile["build_identity"]["libncnn_a_sha256"] = "0" * 64
        with self.assertRaisesRegex(VALIDATOR.ProfileError, "build.libncnn"):
            VALIDATOR.validate_profile(profile, "recommended-dual-thread")

    def test_missing_private_libgomp_is_rejected(self):
        profile = self.load("recommended-dual-thread")
        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory)
            (package / "edgeai_ncnn_image").write_bytes(b"elf")
            identity = {
                "runtime_profile": "recommended-dual-thread",
                "libncnn_a_sha256": VALIDATOR.DUAL_NCNN_SHA256,
                "NCNN_OPENMP": True,
                "NCNN_THREADS": True,
                "NCNN_SIMPLEOMP": False,
                "effective_parallel_backend": "openmp",
                "executable_sha256": VALIDATOR.sha256_file(
                    package / "edgeai_ncnn_image"
                ),
                "private_libgomp_so_1_sha256": VALIDATOR.LIBGOMP_SHA256,
            }
            (package / "runtime_build_identity.json").write_text(
                json.dumps(identity), encoding="utf-8"
            )
            with self.assertRaisesRegex(VALIDATOR.ProfileError, "libgomp is missing"):
                VALIDATOR.validate_package(profile, package)

    def test_wrong_libgomp_hash_is_rejected(self):
        profile = self.load("recommended-dual-thread")
        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory)
            (package / "lib").mkdir()
            (package / "edgeai_ncnn_image").write_bytes(b"elf")
            (package / "lib/libgomp.so.1").write_bytes(b"wrong")
            identity = {
                "runtime_profile": "recommended-dual-thread",
                "libncnn_a_sha256": VALIDATOR.DUAL_NCNN_SHA256,
                "NCNN_OPENMP": True,
                "NCNN_THREADS": True,
                "NCNN_SIMPLEOMP": False,
                "effective_parallel_backend": "openmp",
                "executable_sha256": VALIDATOR.sha256_file(
                    package / "edgeai_ncnn_image"
                ),
                "private_libgomp_so_1_sha256": VALIDATOR.LIBGOMP_SHA256,
            }
            (package / "runtime_build_identity.json").write_text(
                json.dumps(identity), encoding="utf-8"
            )
            with self.assertRaisesRegex(VALIDATOR.ProfileError, "libgomp.sha256"):
                VALIDATOR.validate_package(profile, package)

    def test_valid_dual_package_identity_passes(self):
        profile = self.load("recommended-dual-thread")
        with tempfile.TemporaryDirectory() as directory:
            package = pathlib.Path(directory)
            (package / "lib").mkdir()
            executable = package / "edgeai_ncnn_image"
            libgomp = package / "lib/libgomp.so.1"
            executable.write_bytes(b"elf")
            libgomp.write_bytes(b"gomp")
            executable_hash = VALIDATOR.sha256_file(executable)
            identity = {
                "runtime_profile": "recommended-dual-thread",
                "libncnn_a_sha256": VALIDATOR.DUAL_NCNN_SHA256,
                "NCNN_OPENMP": True,
                "NCNN_THREADS": True,
                "NCNN_SIMPLEOMP": False,
                "effective_parallel_backend": "openmp",
                "executable_sha256": executable_hash,
                "private_libgomp_so_1_sha256": VALIDATOR.LIBGOMP_SHA256,
            }
            (package / "runtime_build_identity.json").write_text(
                json.dumps(identity), encoding="utf-8"
            )

            def fake_hash(path):
                if path == libgomp:
                    return VALIDATOR.LIBGOMP_SHA256
                return executable_hash

            result = VALIDATOR.validate_package(profile, package, fake_hash)
            self.assertEqual(result["private_libgomp"], "PASS")


if __name__ == "__main__":
    unittest.main()
