from pymodaq.control_modules.move_utility_classes import main, comon_parameters_fun

from pymodaq_plugins_slmsuite.resources.daq_move_SlmsuiteBase import DAQ_Move_SlmsuiteBase


class DAQ_Move_SlmsuiteMeadowlark(DAQ_Move_SlmsuiteBase):
    """Meadowlark Optics SLM driven through slmsuite.hardware.slms.meadowlark.Meadowlark

    The Blink SDK of Meadowlark has to be installed (see the slmsuite documentation, the SDK is Windows only).

    Not tested yet on a real device.
    """
    slm_type = 'Meadowlark'
    supported_platforms = ('win32',)  # the Blink SDK driven by slmsuite is a Windows DLL
    params = ([
        {'title': 'Board number:', 'name': 'slm_number', 'type': 'int', 'value': 1, 'min': 1,
         'tip': 'Board number of the SLM, in case of several PCIe SLMs'},
        {'title': 'SDK path:', 'name': 'sdk_path', 'type': 'browsepath', 'value': '', 'filetype': False,
         'tip': 'Folder of the Blink SDK installation. Leave empty to use the default of slmsuite'},
        {'title': 'LUT file:', 'name': 'lut_path', 'type': 'browsepath', 'value': '', 'filetype': True,
         'tip': 'Look-up table file of the SLM. Leave empty to use the default of slmsuite'},
    ] + DAQ_Move_SlmsuiteBase.common_slm_params +
        comon_parameters_fun(DAQ_Move_SlmsuiteBase.is_multiaxes, DAQ_Move_SlmsuiteBase._axis_names,
                             epsilon=DAQ_Move_SlmsuiteBase._epsilons))

    def get_slm_kwargs(self) -> dict:
        kwargs = super().get_slm_kwargs()
        kwargs['slm_number'] = self.settings['slm_number']
        for name in ('sdk_path', 'lut_path'):
            if self.settings[name]:
                kwargs[name] = self.settings[name]
        return kwargs


if __name__ == '__main__':
    main(__file__, init=False)
