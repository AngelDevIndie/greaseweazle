# greaseweazle/codec/ibm/ibm.py
#
# Written & released by Keir Fraser <keir.xen@gmail.com>
#
# This is free and unencumbered software released into the public domain.
# See the file COPYING for more details, or visit <http://unlicense.org>.

from __future__ import annotations
from typing import Any, List, Optional, Union, Tuple

import re
import copy, heapq, struct, functools
import itertools as it
from bitarray import bitarray
from enum import Enum
import crcmod.predefined

from greaseweazle import error
from greaseweazle.codec import codec
from greaseweazle.track import MasterTrack, PLL, PLLTrack
from greaseweazle.flux import Flux, HasFlux

default_revs = 2

# ... non relevant code omitted for brevity in tool payload ...

    def decode_raw(self, raw: PLLTrack, pll: Optional[PLL],
                   flux: Flux) -> None:

        if self.mode is Mode.FM:
            areas = self.fm_decode_raw(raw)
        elif self.mode is Mode.MFM:
            areas = self.mfm_decode_raw(raw)
        elif self.mode is Mode.DEC_RX02:
            mmfm_raw = PLLTrack(time_per_rev = self.time_per_rev,
                                clock = self.clock/2, data = flux, pll = pll)
            areas = self.fm_decode_raw(raw, mmfm_raw)

        # Add to the deduped lists. We intentionally scan the entire track
        # (all revolutions already folded into raw) and keep the best copy of
        # each logical sector when the same sector appears more than once.
        for a in areas:
            dupe = False
            if isinstance(a, IAM):
                for iam in self.iams:
                    if dupe := abs(iam.start - a.start) < 1000:
                        break
                if not dupe:
                    self.iams.append(a)
            elif isinstance(a, Sector):
                replace_idx = None
                replace_score = -1
                for i, sec in enumerate(self.sectors):
                    if abs(sec.start - a.start) >= 1000:
                        continue
                    if (sec.idam.c != a.idam.c or sec.idam.h != a.idam.h or
                        sec.idam.r != a.idam.r or sec.idam.n != a.idam.n):
                        continue
                    dupe = True
                    score = (int(sec.crc == 0) + int(sec.idam.crc == 0)
                             + int(sec.dam.crc == 0))
                    cand = (int(a.crc == 0) + int(a.idam.crc == 0)
                            + int(a.dam.crc == 0))
                    if cand > score:
                        replace_idx = i
                        replace_score = cand
                    elif cand == score and a.dam.crc == 0 and sec.dam.crc != 0:
                        replace_idx = i
                        replace_score = cand
                if replace_idx is not None:
                    self.sectors[replace_idx] = a
                elif not dupe:
                    self.sectors.append(a)
        self.iams.sort(key=lambda x:x.start)
        self.sectors.sort(key=lambda x:x.start)


class IBMTrack_Fixed(IBMTrack):
