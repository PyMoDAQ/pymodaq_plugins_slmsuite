from typing import Optional

import numpy as np

from pymodaq_gui.parameter import Parameter
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_plugins_beam_shaping.algorithms import AlgoBase
from pymodaq_plugins_beam_shaping.algorithms.factory import AlgorithmFactory
from pymodaq_plugins_beam_shaping.algorithms.utils import AlgoType, LensSetup

from slmsuite.holography.algorithms import Hologram
from slmsuite.misc.xp import as_numpy

logger = set_logger(get_module_name(__file__))

# Parameters used by each method of Hologram.optimize with the default value slmsuite gives them (ALGORITHM_DEFAULTS in
# slmsuite/holography/algorithms/_header.py, checked by the tests). The GPU (cupy) is used by slmsuite if installed.
METHOD_DEFAULTS: dict[str, dict[str, float]] = {
    'GS': {},
    'WGS-Leonardo': {'feedback_exponent': 0.8},
    'WGS-Kim': {'feedback_exponent': 0.8, 'fix_phase_iteration': 10},
    'WGS-Nogrette': {'feedback_factor': 0.1},
    'WGS-Wu': {'feedback_exponent': 0.5},
    'WGS-tanh': {'feedback_factor': 0.2, 'feedback_exponent': 0.5},
}


@AlgorithmFactory.register_algorithm()
class SlmsuiteHologram(AlgoBase):
    """ Gerchberg-Saxton and weighted Gerchberg-Saxton phase retrieval, computed by slmsuite

    The phase is computed with slmsuite.holography.algorithms.Hologram (``optimize``), in the Fourier plane of a lens
    as for the Gerchberg-Saxton algorithm of BeamShaping: the input beam amplitude is the nearfield amplitude and the
    target amplitude is the farfield one. Each step runs ``Iterations per step`` iterations of the chosen method and
    keeps the state of the optimization (weights, fixed farfield phase for WGS-Kim) from step to step. Changing the
    input beam, the target, or the initial phase restarts the optimization.

    * GS: Gerchberg-Saxton
    * WGS-Leonardo: https://doi.org/10.1364/OE.15.001913
    * WGS-Kim: https://doi.org/10.1364/OL.44.003178
    * WGS-Nogrette: https://doi.org/10.1103/PhysRevX.4.021034
    * WGS-Wu: https://doi.org/10.1364/OE.413723
    * WGS-tanh: weights updated with a hyperbolic tangent

    The weighted methods give a uniform intensity on a set of spots or regions better than GS. See the documentation of
    slmsuite (``Hologram.optimize``) for the details of the parameters.
    """
    ALGO_NAME = 'slmsuite Hologram'
    ALGOTYPE = AlgoType.AMPLITUDE
    SETUP_TYPE = LensSetup.TwoF
    ITERATIVE = True
    MANUAL_LOOP = True

    params = [
        {'title': 'Method:', 'name': 'method', 'type': 'list', 'limits': list(METHOD_DEFAULTS), 'value': 'GS'},
        {'title': 'Iterations per step:', 'name': 'iterations', 'type': 'int', 'value': 1, 'min': 1},
        {'title': 'Feedback exponent:', 'name': 'feedback_exponent', 'type': 'float', 'value': 0.8, 'visible': False,
         'tip': 'Power of the weighting (WGS-Leonardo, WGS-Kim, WGS-Wu, WGS-tanh)'},
        {'title': 'Feedback factor:', 'name': 'feedback_factor', 'type': 'float', 'value': 0.1, 'visible': False,
         'tip': 'Gain of the weighting (WGS-Nogrette), maximal relative change of the weights (WGS-tanh)'},
        {'title': 'Fix phase at iteration:', 'name': 'fix_phase_iteration', 'type': 'int', 'value': 10, 'min': 0,
         'visible': False,
         'tip': 'WGS-Kim: the farfield phase is fixed after this number of iterations'},
    ]

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._hologram: Optional[Hologram] = None
        self._last_phase: Optional[np.ndarray] = None  # modulator phase set by the last step

    def value_changed(self, param: Parameter):
        if param.name() == 'method':
            self._update_settings_for_method(param.value())
        if self.parent_app is not None:
            self.parent_app.algo_settings_changed()

    def _update_settings_for_method(self, method: str):
        """Show the settings used by the method and reset them to its defaults"""
        defaults = METHOD_DEFAULTS[method]
        with self.settings.treeChangeBlocker():
            for name in ('feedback_exponent', 'feedback_factor', 'fix_phase_iteration'):
                child = self.settings.child(name)
                child.setOpts(visible=name in defaults)
                if name in defaults:
                    child.setValue(defaults[name])

    def do_things_after_set_input(self):
        self._hologram = None

    def do_things_after_set_target(self):
        self._hologram = None

    def _method_kwargs(self) -> dict[str, float]:
        method = self.settings['method']
        return {name: self.settings[name] for name in METHOD_DEFAULTS[method]}

    def _build_hologram(self) -> Hologram:
        """Start a new optimization from the current phase of the modulator field"""
        shape = self._modulator_field.shape
        return Hologram(target=np.asarray(self._target_field.amplitude, dtype=float),
                        amp=np.asarray(self._input_field.amplitude, dtype=float),
                        phase=np.asarray(self._modulator_field.phase, dtype=float),
                        slm_shape=shape)

    def compute_phase(self, do_step=True, **kwargs):
        # the modulator phase differs from the last one we set when the user reset the initial phase: start again
        if (self._hologram is None or self._last_phase is None or
                not np.array_equal(self._modulator_field.phase, self._last_phase)):
            self._hologram = self._build_hologram()

        self._hologram.optimize(method=self.settings['method'], maxiter=self.settings['iterations'],
                                verbose=False, **self._method_kwargs())

        self.set_phase_in_modulator_plane(np.asarray(as_numpy(self._hologram.get_phase()), dtype=float))
        self._last_phase = self._modulator_field.phase.copy()
        self.compute_forward_fft(update_plots=False)  # the output field shown corresponds to the new phase


if __name__ == '__main__':
    pass
