from pymodaq.control_modules.move_utility_classes import main, comon_parameters_fun

from pymodaq_plugins_slmsuite.resources.daq_move_SlmsuiteBase import DAQ_Move_SlmsuiteBase


class DAQ_Move_SlmsuiteSimulated(DAQ_Move_SlmsuiteBase):
    """Simulated SLM (slmsuite.hardware.slms.simulated.SimulatedSLM): no hardware needed

    Useful to test a Dashboard, or an extension such as BeamShaping, without a real SLM.
    """
    slm_type = 'SimulatedSLM'
    params = ([
        {'title': 'Width (pixels):', 'name': 'sim_width', 'type': 'int', 'value': 1920, 'min': 1},
        {'title': 'Height (pixels):', 'name': 'sim_height', 'type': 'int', 'value': 1080, 'min': 1},
        {'title': 'Pixel pitch (um):', 'name': 'pitch_um', 'type': 'float', 'value': 8., 'min': 0.1},
    ] + DAQ_Move_SlmsuiteBase.common_slm_params +
        comon_parameters_fun(DAQ_Move_SlmsuiteBase.is_multiaxes, DAQ_Move_SlmsuiteBase._axis_names,
                             epsilon=DAQ_Move_SlmsuiteBase._epsilons))

    def get_slm_kwargs(self) -> dict:
        kwargs = super().get_slm_kwargs()
        kwargs.update(resolution=(self.settings['sim_width'], self.settings['sim_height']),
                      pitch_um=(self.settings['pitch_um'], self.settings['pitch_um']))
        return kwargs


if __name__ == '__main__':
    main(__file__, init=False)
