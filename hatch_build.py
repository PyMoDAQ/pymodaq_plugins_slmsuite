from pathlib import Path
from hatchling.metadata.plugin.interface import MetadataHookInterface
from pymodaq_utils.resources.hatch_build_plugins import update_metadata_from_toml

here = Path(__file__).absolute().parent


class PluginInfoTomlHook(MetadataHookInterface):
    def update(self, metadata: dict) -> None:
        update_metadata_from_toml(metadata, here)
        # algorithms discovered by the BeamShaping extension of pymodaq_plugins_beam_shaping
        metadata.setdefault('entry-points', {})['pymodaq_plugins_beam_shaping.algorithms'] = {
            'slmsuite': 'pymodaq_plugins_slmsuite.algorithms'}
