# Fingerprint patch validation

Validated baseline: crDroid `android_hardware_xiaomi`, branch `16.0`, commit
`3bf83ab759e0b1a8c2c6bc54b137a2b0549ff77f`.

```sh
python3 device/xiaomi/dada/patches/tests/test_fingerprint_patches.py hardware/xiaomi
```

Pass an **unpatched** checkout. The script applies the eight fingerprint patches
in a temporary tree and leaves your checkout unchanged. Other hardware/xiaomi
patches are outside this check.

The lockout fixture compiles the patched `resetLockout()` and notification
blocks directly from `Session.cpp`, with mock status, callback, tracker and
vendor interfaces. It tests the vendor call/HAT path in local `kNone`, rejected
resets, synchronous and late completion callbacks, repeated requests, the
locked-state callback path, error suppression, and callback lifetime.

The fixture uses AddressSanitizer and UndefinedBehaviorSanitizer. On runners
where LeakSanitizer cannot access `/proc`, use `ASAN_OPTIONS=detect_leaks=0`.
These host checks do not replace a Soong build or real sensor/TEE tests.
