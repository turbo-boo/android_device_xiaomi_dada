#!/usr/bin/env python3
"""Apply the fingerprint series and exercise its actual lockout reset methods."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


def block(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end], source[opening + 1:end - 1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hardware_xiaomi", type=Path, help="Unpatched crDroid hardware/xiaomi")
    args = parser.parse_args()
    tests = Path(__file__).resolve().parent
    patch_dir = tests.parent / "hardware_xiaomi"
    with tempfile.TemporaryDirectory(prefix="dada-fingerprint-") as temp:
        root = Path(temp)
        tree = root / "hardware-xiaomi"
        # Only the fingerprint paths are modified by this series. Leave the
        # caller's checkout and unrelated hardware/xiaomi patches untouched.
        for directory in ("aidl/fingerprint", "fingerprint"):
            shutil.copytree(args.hardware_xiaomi / directory, tree / directory)
        subprocess.run(["git", "init", "-q", str(tree)], check=True)
        for number in ("0001", "0002", "0005", "0006", "0007", "0012", "0013", "0014"):
            patch, = patch_dir.glob(number + "-*.patch")
            subprocess.run(["git", "apply", "--check", str(patch)], cwd=tree, check=True)
            subprocess.run(["git", "apply", "--whitespace=error", str(patch)], cwd=tree, check=True)
            print("PASS apply", patch.name, flush=True)

        source = (tree / "aidl/fingerprint/Session.cpp").read_text()
        reset, _ = block(source, "ndk::ScopedAStatus Session::resetLockout(")
        invalidate, _ = block(source, "void Session::invalidateLockoutReset()")
        _, notify_reset = block(source, "case FINGERPRINT_RESET_LOCKOUT:")
        _, notify_error = block(source, "case FINGERPRINT_ERROR:")
        # The error prelude invalidates a pending fallback. The remaining
        # Android error translation/forwarding is outside this host fixture.
        error_prelude = notify_error[:notify_error.index("int32_t vendorCode")]
        fixture = (tests / "LockoutResetTest.inc").read_text()
        methods = reset.replace("Session::resetLockout", "resetLockout", 1)
        methods += "\n" + invalidate.replace("Session::invalidateLockoutReset", "invalidateLockoutReset", 1)
        methods += "\nvoid vendorReset() {" + notify_reset + "}\n"
        methods += "\nvoid vendorError() {" + error_prelude + "}\n"
        cpp = root / "lockout-test.cpp"
        cpp.write_text(fixture.replace("// SESSION_METHODS", methods))
        executable = root / "lockout-test"
        subprocess.run([
            "c++", "-std=c++17", "-DIMPL_V2", "-pthread", "-g", "-O1",
            "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
            "-fno-omit-frame-pointer", str(cpp), "-o", str(executable)
        ], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
