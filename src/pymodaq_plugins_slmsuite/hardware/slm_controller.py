"""Thin wrapper around the SLM classes of slmsuite.

All the plugins of this package talk to an :class:`SlmController` instead of the slmsuite objects, so that they can be
tested with a fake controller and so that the vendor specific imports (SDKs that are often available on one platform
only) stay lazy.
"""
import inspect
from contextlib import contextmanager
from functools import wraps
from importlib import import_module
from typing import Any

from pymodaq_utils.logger import set_logger, get_module_name

import numpy as np

logger = set_logger(get_module_name(__file__))

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


@contextmanager
def holoeye_without_preview():
    """Open the Holoeye SLM without the SDK preview window

    slmsuite calls ``HEDS.SLM.Init(preselect=...)`` and the SDK opens by default a preview window (which needs a GUI
    thread and may ask for authorizations, making the initialization fail when done from a PyMoDAQ module thread). When
    the ``Init`` function of the installed SDK has an ``openPreview`` argument, it is set to False during the opening.
    """
    heds = getattr(import_module('slmsuite.hardware.slms.holoeye'), 'HEDS', None)
    slm_class = getattr(heds, 'SLM', None)
    init = getattr(slm_class, 'Init', None)
    try:
        has_option = init is not None and 'openPreview' in inspect.signature(init).parameters
    except (TypeError, ValueError):  # no signature available for this callable
        has_option = False
    if not has_option:
        logger.warning('The Holoeye SDK has no openPreview option in SLM.Init (or it cannot be inspected): '
                       'the preview window cannot be disabled')
        yield
        return

    @wraps(init)
    def init_without_preview(*args, **kwargs):
        kwargs.setdefault('openPreview', False)
        return init(*args, **kwargs)

    slm_class.Init = staticmethod(init_without_preview)
    try:
        yield
    finally:
        slm_class.Init = staticmethod(init)


class SlmController:
    """Open one slmsuite SLM and send phase or grey level images to it

    Parameters
    ----------
    slm_type: str
        One of the keys of ``SLM_CLASSES``
    **kwargs:
        Passed to the constructor of the slmsuite class (``wav_um``, ``pitch_um``, ``resolution``, ...), except
        ``preview`` (Holoeye only, default False): whether the SDK preview window is opened.
    """

    def __init__(self, slm_type: str, **kwargs: Any):
        self.slm_type = slm_type
        slm_class = get_slm_class(slm_type)
        preview = kwargs.pop('preview', False)
        if slm_type == 'Holoeye' and not preview:
            with holoeye_without_preview():
                self.slm = slm_class(**kwargs)
        else:
            self.slm = slm_class(**kwargs)

    @property
    def shape(self) -> tuple[int, int]:
        """The shape (height, width) of the SLM in pixels"""
        return tuple(int(s) for s in self.slm.shape)

    @property
    def pitch_um(self) -> tuple[float, float]:
        """The size (x, y) of the pixels in micrometer, as known by slmsuite (the driver when it can tell, else 8 um)"""
        pitch = np.broadcast_to(np.asarray(self.slm.pitch_um, dtype=float), (2,))
        return float(pitch[0]), float(pitch[1])

    @property
    def has_internal_calibration(self) -> bool:
        """True if the SLM converts a phase to grey levels with a calibration of its own: a lookup table known by
        slmsuite, or the one the Meadowlark SDK loads from the hardware"""
        return self.slm_type == 'Meadowlark' or getattr(self.slm, 'lut', None) is not None

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

    def set_wavelength(self, wav_um: float):
        """Change the working wavelength of the open SLM (microns)

        slmsuite reads ``wav_um`` each time it converts a phase into grey levels. The design wavelength follows it if
        it was the same (default of slmsuite), keeping ``phase_scaling`` at 1. The Holoeye SDK also has to know it.
        """
        old = self.slm.wav_um
        if self.slm.wav_design_um == old:
            self.slm.wav_design_um = float(wav_um)
        self.slm.wav_um = float(wav_um)
        slm_lib = getattr(self.slm, 'slm_lib', None)
        if self.slm_type == 'Holoeye' and slm_lib is not None:
            self.slm._handle_error(slm_lib.setWavelength(wav_um * 1000))

    def close(self):
        self.slm.close()
