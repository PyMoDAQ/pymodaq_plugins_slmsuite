"""Thin wrapper around the SLM classes of slmsuite.

All the plugins of this package talk to an :class:`SlmController` instead of the slmsuite objects, so that they can be
tested with a fake controller and so that the vendor specific imports (SDKs that are often available on one platform
only) stay lazy.
"""
from importlib import import_module
from typing import Any

import numpy as np

# name shown in the plugin -> (module, class) in slmsuite.hardware.slms
SLM_CLASSES: dict[str, tuple[str, str]] = {
    'SimulatedSLM': ('slmsuite.hardware.slms.simulated', 'SimulatedSLM'),
    'Holoeye': ('slmsuite.hardware.slms.holoeye', 'Holoeye'),
    'Meadowlark': ('slmsuite.hardware.slms.meadowlark', 'Meadowlark'),
    'Santec': ('slmsuite.hardware.slms.santec', 'Santec'),
    'Hamamatsu': ('slmsuite.hardware.slms.hamamatsu', 'Hamamatsu'),
    'ScreenMirrored': ('slmsuite.hardware.slms.screenmirrored', 'ScreenMirrored'),
}


def get_slm_class(slm_type: str) -> type:
    """Import (lazily) and return the slmsuite class corresponding to a name of ``SLM_CLASSES``"""
    try:
        module_name, class_name = SLM_CLASSES[slm_type]
    except KeyError:
        raise ValueError(f'Unknown SLM type {slm_type}, should be one of {list(SLM_CLASSES)}') from None
    return getattr(import_module(module_name), class_name)


class SlmController:
    """Open one slmsuite SLM and send phase or grey level images to it

    Parameters
    ----------
    slm_type: str
        One of the keys of ``SLM_CLASSES``
    **kwargs:
        Passed to the constructor of the slmsuite class (``wav_um``, ``pitch_um``, ``resolution``, ...)
    """

    def __init__(self, slm_type: str, **kwargs: Any):
        self.slm_type = slm_type
        self.slm = get_slm_class(slm_type)(**kwargs)

    @property
    def shape(self) -> tuple[int, int]:
        """The shape (height, width) of the SLM in pixels"""
        return tuple(int(s) for s in self.slm.shape)

    @property
    def bitresolution(self) -> int:
        """The number of grey levels of the SLM"""
        return int(self.slm.bitresolution)

    def show_phase(self, phase: np.ndarray, phase_correct: bool = True):
        """Display a phase in radians, converted to grey levels by slmsuite (wrapping, LUT, phase correction...)"""
        self.slm.set_phase(np.asarray(phase, dtype=float), phase_correct=phase_correct, settle=False)

    def show_grey_levels(self, grey: np.ndarray):
        """Display grey levels directly, bypassing the phase conversion (values are rounded and clipped)"""
        grey = np.clip(np.rint(np.asarray(grey, dtype=float)), 0, self.bitresolution - 1)
        self.slm.set_phase(grey.astype(self.slm.dtype), settle=False)

    def get_phase(self) -> np.ndarray:
        """The phase (radians) really displayed by the SLM, as a numpy array"""
        phase = self.slm.phase
        return np.asarray(phase.get() if hasattr(phase, 'get') else phase)

    def close(self):
        self.slm.close()
