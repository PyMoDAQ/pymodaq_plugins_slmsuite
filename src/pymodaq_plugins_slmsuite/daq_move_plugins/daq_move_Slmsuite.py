from pymodaq.control_modules.move_utility_classes import main, comon_parameters_fun

from pymodaq_plugins_slmsuite.hardware.slm_controller import SLM_CLASSES
from pymodaq_plugins_slmsuite.resources.daq_move_SlmsuiteBase import (DAQ_Move_SlmsuiteBase, parse_kwargs)


class DAQ_Move_Slmsuite(DAQ_Move_SlmsuiteBase):
    """Actuator displaying a phase (or grey levels) on any SLM supported by slmsuite

    Choose the slmsuite class in ``SLM type`` and give its constructor arguments as a Python dictionary in
    ``Arguments``, for instance ``{'slm_number': 1}`` for a Meadowlark or ``{'preselect': 'index:0'}`` for a Holoeye. See
    the documentation of slmsuite.hardware.slms for the arguments of each class. The vendor SDKs have to be installed
    separately (see the slmsuite documentation).

    Tested only against the simulated SLM of slmsuite, not against real devices.
    """
    params = ([
        {'title': 'SLM type:', 'name': 'slm_type', 'type': 'list', 'limits': list(SLM_CLASSES),
         'value': 'SimulatedSLM'},
        {'title': 'Arguments:', 'name': 'arguments', 'type': 'str', 'value': "{'resolution': (1920, 1080)}",
         'tip': 'Python dictionary of keyword arguments for the constructor of the slmsuite class'},
    ] + DAQ_Move_SlmsuiteBase.common_slm_params +
        comon_parameters_fun(DAQ_Move_SlmsuiteBase.is_multiaxes, DAQ_Move_SlmsuiteBase._axis_names,
                             epsilon=DAQ_Move_SlmsuiteBase._epsilons))

    def get_slm_type(self) -> str:
        return self.settings['slm_type']

    def get_slm_kwargs(self) -> dict:
        kwargs = super().get_slm_kwargs()
        kwargs.update(parse_kwargs(self.settings['arguments']))
        return kwargs


if __name__ == '__main__':
    main(__file__, init=False)
