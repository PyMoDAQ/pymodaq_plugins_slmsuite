import ast
from typing import Any

import numpy as np

from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun, DataActuatorType,
                                                          DataActuator)
from pymodaq_gui.parameter import Parameter
from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_plugins_utils.hardware.shaper import ModulatorType, shaper_params, fill_shaper_settings

from pymodaq_plugins_slmsuite import config
from pymodaq_plugins_slmsuite.hardware.slm_controller import SlmController

logger = set_logger(get_module_name(__file__))


class DAQ_Move_SlmsuiteBase(DAQ_Move_base):
    """Base class of the actuators driving a spatial light modulator (SLM) through slmsuite

    The target of a move is a 2D array (``DataActuator`` with one 2D array, or one value that is spread over the whole
    SLM). It is displayed as a phase in radians, converted to grey levels by slmsuite (wrapping, lookup table, phase
    correction of the wavefront if one was loaded), or, if the ``as_grey_levels`` attribute of the data is True (as
    ``DataShaper`` of pymodaq_plugins_beam_shaping does) or the ``Input as grey levels`` setting is checked, as raw grey
    levels. This is the same interface as the one of the Holoeye plugin and of the mock *Shaper* of BeamShaping.

    Subclasses define ``slm_type`` (a key of ``hardware.slm_controller.SLM_CLASSES``) and ``slm_params`` (the settings
    specific to their SLM) and override ``get_slm_kwargs`` to turn these settings into constructor arguments.
    """
    slm_type: str = None
    slm_params: list = []

    is_multiaxes = False
    _axis_names = ['']
    _controller_units = ''
    _epsilons = 0.1
    data_actuator_type = DataActuatorType.DataActuator
    has_encoder = False  # the SLM cannot be read back: PyMoDAQ takes the target as the current value

    common_slm_params = [
        {'title': 'SLM Infos:', 'name': 'info', 'type': 'group', 'children': [
            {'title': 'Width:', 'name': 'width', 'type': 'int', 'value': 0, 'readonly': True},
            {'title': 'Height:', 'name': 'height', 'type': 'int', 'value': 0, 'readonly': True},
            {'title': 'Grey levels:', 'name': 'levels', 'type': 'int', 'value': 0, 'readonly': True},
        ]},
        {'title': 'Wavelength (nm):', 'name': 'wavelength_nm', 'type': 'float',
         'value': config('slm', 'wavelength_nm'), 'min': 1.,
         'tip': 'Working wavelength, used by slmsuite to convert phases into grey levels. Needs a re-initialization.'},
        {'title': 'Apply phase correction:', 'name': 'phase_correct', 'type': 'bool', 'value': True,
         'tip': 'Add the wavefront correction loaded in slmsuite (if any) to the displayed phases'},
        {'title': 'Input as grey levels:', 'name': 'input_as_grey_levels', 'type': 'bool', 'value': False,
         'tip': 'Interpret the received arrays as grey levels instead of phases in radians'},
    ] + shaper_params()
    params = common_slm_params + comon_parameters_fun(is_multiaxes, _axis_names, epsilon=_epsilons)

    def ini_attributes(self):
        self.controller: SlmController = None

    def get_slm_type(self) -> str:
        """Name of the slmsuite SLM class to open (a key of SLM_CLASSES)"""
        return self.slm_type

    def get_slm_kwargs(self) -> dict[str, Any]:
        """Arguments of the constructor of the slmsuite class. To be extended by the subclasses."""
        return dict(wav_um=self.settings['wavelength_nm'] / 1000)

    def ini_stage(self, controller=None):
        """Open the SLM (master) or use the shared controller (slave)"""
        if self.is_master:
            self.controller = SlmController(self.get_slm_type(), **self.get_slm_kwargs())
        else:
            self.controller = controller

        height, width = self.controller.shape
        self.settings.child('info', 'width').setValue(width)
        self.settings.child('info', 'height').setValue(height)
        fill_shaper_settings(self.settings, self.get_slm_type(), width, height, *self.controller.pitch_um,
                             modulator_type=ModulatorType.PHASE,
                             has_internal_calibration=self.controller.has_internal_calibration)
        self.settings.child('info', 'levels').setValue(self.controller.bitresolution)

        self.current_value = DataActuator(self._title, data=[np.zeros(self.controller.shape)])
        return f'{self.get_slm_type()} SLM {width}x{height} pixels', True

    def close(self):
        if self.is_master and self.controller is not None:
            self.controller.close()

    def commit_settings(self, param: Parameter):
        pass

    def get_actuator_value(self) -> DataActuator:
        """The phase (radians) that the SLM displays"""
        return DataActuator(self._title, data=[self.controller.get_phase()])

    def move_abs(self, value: DataActuator):
        """Display the 2D array of ``value`` on the SLM

        Parameters
        ----------
        value: DataActuator
            One 2D array of the shape of the SLM (height, width), or one value spread over the whole SLM.
        """
        array = np.asarray(value[0])
        if array.size == 1:
            array = np.full(self.controller.shape, array.item())
        if array.shape != self.controller.shape:
            raise ValueError(f'The array to display has shape {array.shape}, the SLM has {self.controller.shape}')

        self.target_value = value
        as_grey = (self.settings['input_as_grey_levels'] or
                   ('as_grey_levels' in value.extra_attributes and bool(value.as_grey_levels)))
        if as_grey:
            self.controller.show_grey_levels(array)
        else:
            self.controller.show_phase(array, phase_correct=self.settings['phase_correct'])
        self.emit_status(ThreadCommand('Update_Status', ['SLM updated']))

    def absolute_difference_condition_to_reach_target(self) -> bool:
        # the array sent is the target, once displayed it is reached: comparing it with the realized phase makes no
        # sense (grey levels, wrapped or quantized phase)
        return True

    def move_rel(self, value: DataActuator):
        self.move_abs(self.current_value + value)

    def move_home(self):
        """Display a null phase"""
        self.controller.show_phase(np.zeros(self.controller.shape))
        self.move_done()

    def stop_motion(self):
        self.move_done()


def parse_kwargs(text: str) -> dict[str, Any]:
    """Parse the content of a free ``Arguments`` setting such as ``{'resolution': (1920, 1080)}``

    Only Python literals are accepted (no code is evaluated)
    """
    text = text.strip()
    if not text:
        return {}
    kwargs = ast.literal_eval(text)
    if not isinstance(kwargs, dict):
        raise ValueError('The arguments should be a Python dictionary, for instance {"slm_number": 1}')
    return kwargs
