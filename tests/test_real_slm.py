"""Manual tests on a REAL SLM, skipped unless the environment variable ``SLMSUITE_REAL_SLM`` is set.

They drive the real plugin class (the same one the Dashboard uses) and display a few patterns that you check by eye on
the SLM. Examples (from the root of the repository)::

    # Meadowlark, board 1
    SLMSUITE_REAL_SLM=Meadowlark SLMSUITE_REAL_ARGS="{'slm_number': 1}" pytest tests/test_real_slm.py -s -v

    # Holoeye, first SLM found
    SLMSUITE_REAL_SLM=Holoeye SLMSUITE_REAL_ARGS="{'preselect': 'index:0'}" pytest tests/test_real_slm.py -s -v

On Windows PowerShell use ``$env:SLMSUITE_REAL_SLM="Meadowlark"`` before calling pytest.

Environment variables:

* ``SLMSUITE_REAL_SLM``: name of the slmsuite class, one of ``hardware.slm_controller.SLM_CLASSES``
* ``SLMSUITE_REAL_ARGS``: constructor arguments as a Python dictionary (see the generic ``Slmsuite`` actuator)
* ``SLMSUITE_REAL_WAVELENGTH_NM``: working wavelength in nm (default 515)
* ``SLMSUITE_REAL_HOLD_S``: seconds each pattern stays displayed (default 3)

What the assertions check is only that nothing raises and that the realized phase read back from slmsuite is coherent
with what was sent. Whether the SLM really shows the pattern, and the wavelength / LUT calibration, are for you to
check by eye (and with a camera) while the patterns are displayed.
"""
import os
import time

import numpy as np
import pytest

from pymodaq.utils.plugin_testing import make_actuator, move_abs_and_wait
from pymodaq.utils.data import DataActuator

from pymodaq_plugins_slmsuite.daq_move_plugins.daq_move_Slmsuite import DAQ_Move_Slmsuite

SLM_TYPE = os.environ.get('SLMSUITE_REAL_SLM')
pytestmark = pytest.mark.skipif(not SLM_TYPE, reason='set SLMSUITE_REAL_SLM to test a real SLM')

HOLD_S = float(os.environ.get('SLMSUITE_REAL_HOLD_S', 3))


def phase_error(displayed: np.ndarray, expected: np.ndarray) -> float:
    """Largest difference modulo 2 pi between two phases"""
    return float(np.abs(np.angle(np.exp(1j * (displayed - expected)))).max())


@pytest.fixture(scope='module')
def slm(qapp):
    plugin = make_actuator(DAQ_Move_Slmsuite, slm_type=SLM_TYPE,
                           arguments=os.environ.get('SLMSUITE_REAL_ARGS', '{}'),
                           wavelength_nm=float(os.environ.get('SLMSUITE_REAL_WAVELENGTH_NM', 515)))
    assert plugin.initialized, 'The SLM could not be opened, see the log above'
    print(f'\n{plugin.init_info}')
    yield plugin
    move_abs_and_wait(plugin, 0.)
    plugin.close()


def show(slm, array: np.ndarray, description: str, **attributes):
    print(f'  displaying: {description} (for {HOLD_S} s)')
    move_abs_and_wait(slm, DataActuator(data=[array], **attributes))
    time.sleep(HOLD_S)


def grid(slm):
    height, width = slm.controller.shape
    return np.meshgrid(np.arange(width), np.arange(height))


def test_zero_phase(slm):
    show(slm, np.zeros(slm.controller.shape), 'phase 0 everywhere (uniform)')
    assert slm.get_actuator_value()[0].shape == slm.controller.shape


def test_ramp_0_to_2pi(slm):
    """Horizontal phase ramp from 0 to 2 pi: a blazed grating with one period over the whole SLM, the zeroth order
    should leave its place"""
    xx, _ = grid(slm)
    phase = 2 * np.pi * xx / xx.shape[1]
    show(slm, phase, 'phase ramp 0 -> 2 pi over the width')
    assert phase_error(slm.get_actuator_value()[0], phase) < 0.2


def test_blazed_grating(slm):
    """Blazed grating of 16 pixels period: a clean first diffraction order should appear"""
    xx, _ = grid(slm)
    phase = 2 * np.pi * xx / 16
    show(slm, phase, 'blazed grating, period 16 pixels')
    assert phase_error(slm.get_actuator_value()[0], np.mod(phase, 2 * np.pi)) < 0.2


def test_two_halves(slm):
    """Left half 0, right half pi: the two halves interfere destructively on axis if the wavelength / LUT are right"""
    xx, _ = grid(slm)
    phase = np.where(xx < xx.shape[1] // 2, 0., np.pi)
    show(slm, phase, 'left half 0, right half pi')
    assert phase_error(slm.get_actuator_value()[0], phase) < 0.2


def test_grey_levels_ramp(slm):
    """Raw grey levels, bypassing slmsuite's phase conversion: horizontal ramp over all the levels"""
    xx, _ = grid(slm)
    levels = slm.controller.bitresolution
    grey = np.floor(xx / xx.shape[1] * levels)
    show(slm, grey, f'raw grey levels ramp 0 -> {levels - 1}', as_grey_levels=True)
    assert np.array_equal(np.asarray(slm.controller.slm.display), grey.astype(slm.controller.slm.dtype))


def test_move_home_blanks_the_slm(slm):
    slm.move_home()
    time.sleep(HOLD_S)
    assert np.abs(slm.get_actuator_value()[0]).max() < 0.1
