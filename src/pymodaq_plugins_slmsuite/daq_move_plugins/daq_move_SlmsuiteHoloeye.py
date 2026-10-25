from pymodaq.control_modules.move_utility_classes import main, comon_parameters_fun

from pymodaq_plugins_slmsuite.resources.daq_move_SlmsuiteBase import DAQ_Move_SlmsuiteBase


class DAQ_Move_SlmsuiteHoloeye(DAQ_Move_SlmsuiteBase):
    """Holoeye SLM (PLUTO, LUNA, GAEA...) driven through slmsuite.hardware.slms.holoeye.Holoeye

    The Holoeye SLM Display SDK has to be installed (see the slmsuite documentation). The plugin pymodaq_plugins_holoeye
    does the same job with the SDK directly.

    Not tested yet on a real device.
    """
    slm_type = 'Holoeye'
    params = ([
        {'title': 'Preselect:', 'name': 'preselect', 'type': 'str', 'value': 'index:0',
         'tip': 'Holoeye selection string, for instance index:0, name:pluto;serial:0001 or serial:2220-0011'},
    ] + DAQ_Move_SlmsuiteBase.common_slm_params +
        comon_parameters_fun(DAQ_Move_SlmsuiteBase.is_multiaxes, DAQ_Move_SlmsuiteBase._axis_names,
                             epsilon=DAQ_Move_SlmsuiteBase._epsilons))

    def get_slm_kwargs(self) -> dict:
        kwargs = super().get_slm_kwargs()
        kwargs['preselect'] = self.settings['preselect']
        return kwargs


if __name__ == '__main__':
    main(__file__, init=False)
