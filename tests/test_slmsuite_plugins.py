"""Behaviour tests of the SLM actuators, against the simulated SLM of slmsuite (no hardware, no visible GUI).

Real devices (Meadowlark, Holoeye...) are not tested here: only the arguments built for their constructor are checked,
with a fake controller.
"""
from types import SimpleNamespace

import numpy as np
import pytest

from pymodaq.utils.plugin_testing import make_actuator, move_abs_and_wait
from pymodaq.utils.data import DataActuator

from pymodaq_plugins_slmsuite.hardware import slm_controller
from pymodaq_plugins_slmsuite.hardware.slm_controller import SlmController
from pymodaq_plugins_slmsuite.resources.daq_move_SlmsuiteBase import parse_kwargs
from pymodaq_plugins_slmsuite.daq_move_plugins.daq_move_Slmsuite import DAQ_Move_Slmsuite
from pymodaq_plugins_slmsuite.daq_move_plugins.daq_move_SlmsuiteSimulated import DAQ_Move_SlmsuiteSimulated
from pymodaq_plugins_slmsuite.daq_move_plugins.daq_move_SlmsuiteMeadowlark import DAQ_Move_SlmsuiteMeadowlark
from pymodaq_plugins_slmsuite.daq_move_plugins.daq_move_SlmsuiteHoloeye import DAQ_Move_SlmsuiteHoloeye

WIDTH, HEIGHT = 64, 48


@pytest.fixture
def slm(qapp):
    plugin = make_actuator(DAQ_Move_SlmsuiteSimulated, sim_width=WIDTH, sim_height=HEIGHT)
    assert plugin.initialized
    yield plugin
    plugin.close()


class TestController:
    def test_unknown_type(self):
        with pytest.raises(ValueError):
            SlmController('NotAnSlm')

    def test_all_names_are_known(self):
        assert set(slm_controller.SLM_CLASSES) >= {'SimulatedSLM', 'Holoeye', 'Meadowlark'}

    def test_simulated_shape_and_levels(self):
        controller = SlmController('SimulatedSLM', resolution=(WIDTH, HEIGHT))
        assert controller.shape == (HEIGHT, WIDTH)
        assert controller.bitresolution == 256
        controller.close()

    def test_grey_levels_are_clipped_and_rounded(self):
        controller = SlmController('SimulatedSLM', resolution=(WIDTH, HEIGHT))
        controller.show_grey_levels(np.full((HEIGHT, WIDTH), 300.4))
        assert np.all(controller.slm.display == 255)
        controller.close()


class TestParseKwargs:
    def test_empty(self):
        assert parse_kwargs('  ') == {}

    def test_literal(self):
        assert parse_kwargs("{'slm_number': 2, 'resolution': (10, 20)}") == {'slm_number': 2, 'resolution': (10, 20)}

    def test_no_code_evaluated(self):
        with pytest.raises(ValueError):
            parse_kwargs("__import__('os').getcwd()")

    def test_not_a_dict(self):
        with pytest.raises(ValueError):
            parse_kwargs('[1, 2]')


def _geometry(plugin):
    group = plugin.settings.child('shaper_geometry')
    return [group[name] for name in ('width', 'height', 'pixel_size_x', 'pixel_size_y')]


def _properties(plugin):
    group = plugin.settings.child('shaper_properties')
    return [group[name] for name in ('name', 'has_internal_calibration', 'use_internal_calibration')]


class TestShaperGeometry:
    def test_simulated(self, slm):
        width, height, size_x, size_y = _geometry(slm)
        assert (width, height) == (WIDTH, HEIGHT)
        assert size_x > 0 and size_y > 0

    def test_pitch_from_slmsuite(self):
        controller = SlmController('SimulatedSLM', resolution=(WIDTH, HEIGHT), pitch_um=(5., 6.))
        assert controller.pitch_um == (5., 6.)
        controller.close()

    def test_pitch_given_once(self):
        controller = SlmController('SimulatedSLM', resolution=(WIDTH, HEIGHT), pitch_um=7.)
        assert controller.pitch_um == (7., 7.)
        controller.close()

    def test_fake_controller(self, qapp, fake_controller):
        plugin = make_actuator(DAQ_Move_SlmsuiteMeadowlark)
        assert _geometry(plugin) == [6, 4, 8., 9.]
        assert _properties(plugin) == ['Meadowlark', True, True]
        plugin.close()

    def test_no_internal_calibration_by_default(self, slm):
        assert _properties(slm) == ['SimulatedSLM', False, False]

    def test_lut_is_an_internal_calibration(self):
        controller = SlmController('SimulatedSLM', resolution=(WIDTH, HEIGHT))
        assert not controller.has_internal_calibration
        controller.slm.lut = np.arange(256)
        assert controller.has_internal_calibration
        controller.close()


class TestSimulatedActuator:
    def test_infos(self, slm):
        assert slm.settings['info', 'width'] == WIDTH
        assert slm.settings['info', 'height'] == HEIGHT
        assert slm.settings['info', 'levels'] == 256

    def test_phase_is_displayed_wrapped(self, slm):
        phase = np.linspace(-1, 7, WIDTH * HEIGHT).reshape(HEIGHT, WIDTH)
        move_abs_and_wait(slm, DataActuator(data=[phase]))
        displayed = slm.get_actuator_value()[0]
        expected = np.mod(phase, 2 * np.pi)
        error = np.abs(np.angle(np.exp(1j * (displayed - expected))))
        assert error.max() < 2 * np.pi / 256 * 1.5  # quantization to 256 levels

    def test_single_value_fills_the_slm(self, slm):
        move_abs_and_wait(slm, 1.)
        displayed = slm.get_actuator_value()[0]
        assert displayed.shape == (HEIGHT, WIDTH)
        assert np.ptp(displayed) < 2 * np.pi / 256 * 1.5

    def test_grey_levels_with_setting(self, slm):
        slm.settings.child('input_as_grey_levels').setValue(True)
        grey = np.tile(np.arange(WIDTH) * 4, (HEIGHT, 1))
        move_abs_and_wait(slm, DataActuator(data=[grey.astype(float)]))
        assert np.array_equal(slm.controller.slm.display, grey.astype(np.uint8))

    def test_grey_levels_with_data_attribute(self, slm):
        grey = np.full((HEIGHT, WIDTH), 42.)
        move_abs_and_wait(slm, DataActuator(data=[grey], as_grey_levels=True))
        assert np.all(slm.controller.slm.display == 42)

    def test_wrong_shape_is_refused(self, slm):
        with pytest.raises(ValueError):
            slm.move_abs(DataActuator(data=[np.zeros((3, 3))]))

    def test_move_rel(self, slm):
        move_abs_and_wait(slm, DataActuator(data=[np.full((HEIGHT, WIDTH), 1.)]))
        slm.move_rel(DataActuator(data=[np.full((HEIGHT, WIDTH), 0.5)]))
        assert np.abs(slm.get_actuator_value()[0] - 1.5).max() < 2 * np.pi / 256 * 1.5

    def test_close_only_by_master(self, slm):
        slave = make_actuator(DAQ_Move_SlmsuiteSimulated, controller=slm.controller)
        assert slave.controller is slm.controller
        slave.close()  # must not close the shared controller
        move_abs_and_wait(slm, 0.)


def test_generic_plugin_with_arguments(qapp):
    plugin = make_actuator(DAQ_Move_Slmsuite, slm_type='SimulatedSLM',
                           arguments=f"{{'resolution': ({WIDTH}, {HEIGHT})}}")
    assert plugin.initialized
    assert plugin.controller.shape == (HEIGHT, WIDTH)
    move_abs_and_wait(plugin, 0.5)
    plugin.close()


class FakeController:
    instances = []

    def __init__(self, slm_type, **kwargs):
        self.slm_type, self.kwargs = slm_type, kwargs
        self.shape = (4, 6)
        self.pitch_um = (8., 9.)
        self.has_internal_calibration = slm_type == 'Meadowlark'
        self.bitresolution = 256
        FakeController.instances.append(self)

    def close(self):
        pass


@pytest.fixture
def fake_controller(monkeypatch):
    FakeController.instances.clear()
    monkeypatch.setattr('pymodaq_plugins_slmsuite.resources.daq_move_SlmsuiteBase.SlmController', FakeController)
    return FakeController


def test_meadowlark_arguments(qapp, fake_controller):
    plugin = make_actuator(DAQ_Move_SlmsuiteMeadowlark, slm_number=2, wavelength_nm=800.)
    assert plugin.initialized
    controller = fake_controller.instances[-1]
    assert controller.slm_type == 'Meadowlark'
    assert controller.kwargs == {'wav_um': pytest.approx(0.8), 'slm_number': 2}  # empty paths are not passed
    plugin.close()


def test_holoeye_arguments(qapp, fake_controller):
    plugin = make_actuator(DAQ_Move_SlmsuiteHoloeye, preselect='name:pluto')
    controller = fake_controller.instances[-1]
    assert controller.slm_type == 'Holoeye'
    assert controller.kwargs['preselect'] == 'name:pluto'
    assert controller.kwargs['preview'] is False
    plugin.close()


class FakeHEDS:
    class SDK:
        @staticmethod
        def Init(major, minor):
            return 0

    class SLM:
        calls = []

        @staticmethod
        def Init(preselect='', openPreview=True):
            FakeHEDS.SLM.calls.append((preselect, openPreview))
            raise RuntimeError('stop after the SDK call')


class FakeHEDSWithoutOption(FakeHEDS):
    class SLM:
        calls = []

        @staticmethod
        def Init(preselect=''):
            FakeHEDSWithoutOption.SLM.calls.append((preselect,))
            raise RuntimeError('stop after the SDK call')


def _open_holoeye(monkeypatch, heds, **kwargs):
    from slmsuite.hardware.slms import holoeye
    init = heds.SLM.Init
    monkeypatch.setattr(holoeye, 'HEDS', heds)
    monkeypatch.setattr(holoeye, 'heds_types', SimpleNamespace(HEDSERR_NoError=0), raising=False)
    heds.SLM.calls.clear()
    with pytest.raises(RuntimeError, match='stop after'):
        slm_controller.SlmController('Holoeye', preselect='index:0', **kwargs)
    assert heds.SLM.Init is init  # restored


def test_holoeye_preview_disabled_by_default(monkeypatch):
    _open_holoeye(monkeypatch, FakeHEDS)
    assert FakeHEDS.SLM.calls == [('index:0', False)]


def test_holoeye_preview_can_be_enabled(monkeypatch):
    _open_holoeye(monkeypatch, FakeHEDS, preview=True)
    assert FakeHEDS.SLM.calls == [('index:0', True)]


def test_holoeye_sdk_without_preview_option(monkeypatch):
    _open_holoeye(monkeypatch, FakeHEDSWithoutOption)
    assert FakeHEDSWithoutOption.SLM.calls == [('index:0',)]
