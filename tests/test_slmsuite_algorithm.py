import numpy as np
import pytest

pytest.importorskip('pymodaq_plugins_beam_shaping')

from slmsuite.holography.algorithms import ALGORITHM_DEFAULTS

from pymodaq_plugins_beam_shaping.algorithms import factory
from pymodaq_plugins_beam_shaping.algorithms.factory import AlgorithmFactory
from pymodaq_plugins_beam_shaping.field import Field

from pymodaq_plugins_slmsuite.algorithms import slmsuite_hologram
from pymodaq_plugins_slmsuite.algorithms.slmsuite_hologram import SlmsuiteHologram, METHOD_DEFAULTS


@pytest.fixture
def algo(qtbot):
    algo = SlmsuiteHologram()
    shape = algo.shape
    y, x = np.indices(shape)
    r2 = (x - shape[1] / 2) ** 2 + (y - shape[0] / 2) ** 2
    algo.set_input_field(Field('input', amplitude=np.exp(-r2 / (2 * (shape[0] / 6) ** 2))))

    target = np.zeros(shape)
    cy, cx = shape[0] // 2, shape[1] // 2
    for dy, dx in ((-12, -12), (-12, 12), (12, -12), (12, 12)):
        target[cy + dy, cx + dx] = 1
    algo.set_target_field(Field('target', amplitude=target))
    algo.define_input_phase(np.zeros(shape))
    return algo


def efficiency_on_spots(algo):
    target = algo._target_field.amplitude > 0
    intensity = algo.intensity_output
    return intensity[target].sum() / intensity.sum()


def test_registered():
    assert AlgorithmFactory.algorithms_registry[SlmsuiteHologram.ALGO_NAME] is SlmsuiteHologram


@pytest.mark.parametrize('method, defaults', METHOD_DEFAULTS.items())
def test_method_defaults_follow_slmsuite(method, defaults):
    slm_defaults = ALGORITHM_DEFAULTS[method]
    for name, value in defaults.items():
        assert slm_defaults[name] == value


@pytest.mark.parametrize('method', list(METHOD_DEFAULTS))
def test_method_concentrates_light_on_spots(algo, method):
    algo.settings.child('method').setValue(method)
    algo.settings.child('iterations').setValue(5)
    algo.compute_phase()
    first = efficiency_on_spots(algo)
    for _ in range(3):
        algo.compute_phase()
    assert efficiency_on_spots(algo) >= first > 0.05
    assert np.all(np.isfinite(algo.modulator_field.phase))


def test_optimization_state_is_kept_between_steps(algo):
    algo.compute_phase()
    hologram = algo._hologram
    algo.compute_phase()
    assert algo._hologram is hologram


def test_restart_when_initial_phase_or_target_changes(algo):
    algo.compute_phase()
    hologram = algo._hologram

    algo.define_input_phase(np.random.random(algo.shape))
    algo.compute_phase()
    assert algo._hologram is not hologram

    hologram = algo._hologram
    algo.do_things_after_set_target()
    algo.compute_phase()
    assert algo._hologram is not hologram


def test_method_changes_visible_settings(algo):
    algo.settings.child('method').setValue('WGS-Kim')
    assert algo.settings.child('fix_phase_iteration').opts['visible']
    assert algo.settings.child('feedback_exponent').opts['visible']
    assert not algo.settings.child('feedback_factor').opts['visible']
    algo.settings.child('method').setValue('GS')
    assert not algo.settings.child('feedback_exponent').opts['visible']


def test_discovered_through_entry_point():
    modules = factory.register_external_algorithms()
    assert slmsuite_hologram.__package__ in [m.__name__ for m in modules]
    assert AlgorithmFactory.algorithms_registry[SlmsuiteHologram.ALGO_NAME] is SlmsuiteHologram
