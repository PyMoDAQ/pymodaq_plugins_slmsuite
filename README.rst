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

Tested against the simulated SLM of slmsuite only (``pytest``). The Meadowlark and Holoeye actuators have not been
validated on real devices yet.


BeamShaping algorithm
=====================

With ``pip install pymodaq_plugins_slmsuite[beamshaping]`` the ``slmsuite Hologram`` algorithm is added to the
BeamShaping extension of ``pymodaq_plugins_beam_shaping`` (found through the ``pymodaq_plugins_beam_shaping.algorithms``
entry point). It computes the phase mask with ``slmsuite.holography.algorithms.Hologram``, with the methods GS,
WGS-Leonardo, WGS-Kim, WGS-Nogrette, WGS-Wu and WGS-tanh. The GPU is used if ``cupy`` is installed.
The conjugate gradient method is not exposed yet.


Installation instructions
=========================

* PyMoDAQ 5.3.x, slmsuite >= 0.5.0 (installed with this plugin)
* The vendor SDK of your SLM has to be installed separately, see the
  `slmsuite documentation <https://slmsuite.readthedocs.io/>`_ for each manufacturer.
* Development: ``pip install -e .``, then ``check_plugin`` and ``pytest`` (needs ``pytest-qt``)
