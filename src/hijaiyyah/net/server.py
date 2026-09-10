"""`HCServer` was never a server. It is the receiver, and now it says so.

This file held a class that printed one line and had no caller anywhere in
the tree. The name announced an HTTP server; the role reserved for it was a
receiver of an output range -- the module that catches the wave and returns
something discrete. `teknologi/ISTILAH.md` recorded that mismatch as an open
naming problem in the same class as `OP_MSB` and the Psi / H* collision: a
name that tells the reader the wrong role.

The role is implemented now, in `receiver.RangeReceiver`, named for what it
does. `HCServer` stays as an alias because a name in a shipped glossary is
not deleted quietly -- but it is the same object, so there is one
implementation and no second one drifting behind the old name.
"""
from __future__ import annotations

from ..receiver.rx import RangeReceiver

__all__ = ["HCServer", "RangeReceiver"]

#: Deprecated spelling of `receiver.RangeReceiver`. Same class, not a subclass:
#: an alias cannot drift from what it aliases.
HCServer = RangeReceiver
