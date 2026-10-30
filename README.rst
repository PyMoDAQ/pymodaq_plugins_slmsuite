pymodaq_plugins_slmsuite
########################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_slmsuite.svg
   :target: https://pypi.org/project/pymodaq_plugins_slmsuite/
   :alt: Latest Version

.. image:: https://github.com/PyMoDAQ/pymodaq_plugins_slmsuite/workflows/Upload%20Python%20Package/badge.svg
   :target: https://github.com/PyMoDAQ/pymodaq_plugins_slmsuite
   :alt: Publication Status

PyMoDAQ plugin giving access to the spatial light modulators (SLM) supported by
`slmsuite <https://github.com/slmsuite/slmsuite>`_ (Holoeye, Meadowlark, Santec, Hamamatsu, mirrored screens, ...).
It is meant to be used with the BeamShaping extension of
`pymodaq_plugins_beam_shaping <https://github.com/PyMoDAQ/pymodaq_plugins_beam_shaping>`_, but any Dashboard can use
the actuators.

This branch targets **PyMoDAQ 5.3.x** (Python 3.10 to 3.13).

Authors
=======

* Sebastien J. Weber  (sebastien.weber@cemes.fr)


Instruments
===========

Actuators
+++++++++

All the actuators have the same interface: the target is a 2D array of the shape of the SLM (or a single value spread
over the SLM). It is displayed as a **phase in radians**, converted to grey levels by slmsuite (wrapping, look-up table,
wavefront correction if one was loaded), or as **raw grey levels** if the ``Input as grey levels`` setting is checked or
if the data carries the attribute ``as_grey_levels=True`` (as ``DataShaper`` of BeamShaping does). This is also the
interface of the Holoeye plugin and of the mock *Shaper* of BeamShaping.

* **Slmsuite**: generic, choose the slmsuite class (``SLM type``) and give its constructor arguments as a Python
  dictionary (``Arguments``)
* **SlmsuiteSimulated**: simulated SLM of slmsuite, no hardware needed
* **SlmsuiteMeadowlark**: Meadowlark SLM (Windows only, Blink SDK)
* **SlmsuiteHoloeye**: Holoeye SLM (SLM Display SDK)

Another SLM supported by slmsuite with specific settings can be added by subclassing
``pymodaq_plugins_slmsuite.resources.daq_move_SlmsuiteBase.DAQ_Move_SlmsuiteBase``.

The working wavelength (``Wavelength (nm)`` setting, default in the configuration file of the plugin) is given to
slmsuite to convert phases into grey levels.

Status
++++++

The simulated SLM of slmsuite is tested automatically (``pytest``). The Meadowlark and Holoeye actuators have been
validated on real devices by the maintainer.


BeamShaping algorithms
======================

The BeamShaping extension of ``pymodaq_plugins_beam_shaping`` computes the phase (or amplitude) mask to display on the
SLM with an *algorithm* chosen in its interface. The algorithms are discovered at startup: the ones of
``pymodaq_plugins_beam_shaping`` itself (*Gerchberg-Saxton*, *Projections*, *Direct*, *Diffractive*, *Minimize*,
*TorchOptim*, ...) and the ones that other installed packages declare in the ``pymodaq_plugins_beam_shaping.algorithms``
entry point. This plugin declares one of them, so that the slmsuite algorithms can be used next to the others, on the
same input beam and target, and sent to any of the actuators above (or to the Holoeye or mock *Shaper* actuators).

Installation and use
++++++++++++++++++++

* ``pip install pymodaq_plugins_slmsuite[beamshaping]`` installs ``pymodaq_plugins_beam_shaping`` together with this
  plugin. Without this extra, the actuators work but the algorithm is not available.
* In the Dashboard, name the SLM actuator ``Shaper`` (the extension sends the mask to the actuator of this name) and
  start the BeamShaping extension.
* Choose the algorithm in the algorithm settings of the extension: ``slmsuite Hologram`` appears in the list with the
  others. Switching from one algorithm to another keeps the same input beam and target, so the results can be compared
  directly (output plots, loss/stopping criteria of the extension).
* The extension reads the number of pixels, the pixel size and whether the SLM has an internal calibration from the
  ``Shaper`` actuator itself (the ``shaper_geometry`` and ``shaper_properties`` settings groups defined in
  ``pymodaq_plugins_utils``), which these actuators fill when initialized.

``slmsuite Hologram`` algorithm
+++++++++++++++++++++++++++++++

It computes the phase with ``slmsuite.holography.algorithms.Hologram.optimize``, in the Fourier plane of a lens (the
same setup as the *Gerchberg-Saxton* algorithm of BeamShaping): the amplitude of the input beam is the nearfield
amplitude and the target amplitude is the farfield one. It is iterative: each step runs ``Iterations per step``
iterations of the chosen ``Method`` and keeps the state of the optimization (weights, fixed farfield phase for WGS-Kim)
from step to step. Changing the input beam, the target or the initial phase restarts the optimization.

========================  ==================================================  ==============================================
Method                    Reference                                           Specific settings
========================  ==================================================  ==============================================
GS                        Gerchberg-Saxton                                    none
WGS-Leonardo              https://doi.org/10.1364/OE.15.001913                ``Feedback exponent`` (0.8)
WGS-Kim                   https://doi.org/10.1364/OL.44.003178                ``Feedback exponent`` (0.8),
                                                                              ``Fix phase at iteration`` (10)
WGS-Nogrette              https://doi.org/10.1103/PhysRevX.4.021034           ``Feedback factor`` (0.1)
WGS-Wu                    https://doi.org/10.1364/OE.413723                   ``Feedback exponent`` (0.5)
WGS-tanh                  weights updated with a hyperbolic tangent           ``Feedback factor`` (0.2),
                                                                              ``Feedback exponent`` (0.5)
========================  ==================================================  ==============================================

The values in parentheses are the defaults of slmsuite, restored when the method is changed. The weighted (WGS)
methods give a more uniform intensity on a set of spots or regions than GS. The GPU is used if ``cupy`` is installed.
The conjugate gradient method of slmsuite is not exposed yet. See the documentation of slmsuite
(``Hologram.optimize``) for the details of the parameters.

Adding your own algorithm
+++++++++++++++++++++++++

Any package can add algorithms to the extension: write a subclass of
``pymodaq_plugins_beam_shaping.algorithms.AlgoBase`` decorated with
``@AlgorithmFactory.register_algorithm()`` (see ``pymodaq_plugins_slmsuite/algorithms/slmsuite_hologram.py`` for a
complete example) and declare the module that holds it in the ``pymodaq_plugins_beam_shaping.algorithms`` entry point
of its ``pyproject.toml``. For this plugin the entry point is added in ``hatch_build.py``.


Installation instructions
=========================

* PyMoDAQ 5.3.x, slmsuite >= 0.5.0 (installed with this plugin)
* The vendor SDK of your SLM has to be installed separately, see the
  `slmsuite documentation <https://slmsuite.readthedocs.io/>`_ for each manufacturer.
* Development: ``pip install -e .``, then ``check_plugin`` and ``pytest`` (needs ``pytest-qt``)
