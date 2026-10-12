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

# ... existing code unchanged ...

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

        # Add to the deduped lists. Prefer the best valid copy of each
        # logical sector across multiple revolutions rather than the first
        # match by raw bit offset. This avoids duplicate sector records when a
        # track contains repeated revolutions from an SCP dump.
        for a in areas:
            dupe = False
            if isinstance(a, IAM):
                for iam in self.iams:
                    if dupe := abs(iam.start - a.start) < 1000:
                        break
                if not dupe:
                    self.iams.append(a)
            elif isinstance(a, Sector):
                key = (a.idam.c, a.idam.h, a.idam.r, a.idam.n)
                for i, sec in enumerate(self.sectors):
                    if (sec.idam.c, sec.idam.h, sec.idam.r, sec.idam.n) == key:
                        dupe = True
                        if sec.crc != 0 and a.crc == 0:
                            self.sectors[i] = a
                        break
                if not dupe:
                    self.sectors.append(a)
        self.iams.sort(key=lambda x:x.start)
        self.sectors.sort(key=lambda x:x.start)


class IBMTrack_Fixed(IBMTrack):
