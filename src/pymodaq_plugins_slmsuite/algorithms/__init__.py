"""Algorithms for the BeamShaping extension (pymodaq_plugins_beam_shaping)

This package is declared in the entry point group *pymodaq_plugins_beam_shaping.algorithms*: BeamShaping imports it at
startup, which registers the algorithms below in its algorithm factory. It needs pymodaq_plugins_beam_shaping to be
installed (extra *beamshaping* of this plugin).
"""
from pymodaq_plugins_slmsuite.algorithms import slmsuite_hologram  # noqa: F401  (registers the algorithm)
