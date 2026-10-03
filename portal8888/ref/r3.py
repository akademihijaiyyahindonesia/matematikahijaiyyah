#!/usr/bin/env python3
"""R3 mutations for the canonical Portal v1 sealed body."""
import hashlib
import sys

import portal_ref as p

keys, frame, fields, body, tag = p.sample()
key = keys[fields["port"]]
checks = {
    "body field changed": p.seal(key, p.sealed_body(dev=p.DEV, **(fields | {"status": fields["status"] ^ 1}))) != tag,
    "SOF timestamp displaced": p.seal(key, p.sealed_body(dev=p.DEV, **(fields | {"t_tick": fields["t_tick"] + 1}))) != tag,
    "frame hash mismatched": p.seal(key, p.sealed_body(dev=p.DEV, **(fields | {"frame_hash": hashlib.sha256(frame + b"x").digest()}))) != tag,
}
failed = [name for name, detected in checks.items() if not detected]
for name, detected in checks.items():
    print(f"R3 {name}: {'detected' if detected else 'MISSED'}")
print(f"R3 reference: {len(checks) - len(failed)}/{len(checks)} detected")
sys.exit(bool(failed))
