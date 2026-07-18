# Decompiled with pycdc from Ableton Live 12 (Python 3.11).
# Some functions may be partial: pycdc cannot fully decompile 3.11 bytecode.

# Source Generated with Decompyle++
# File: __init__.pyc (Python 3.11)

from ableton.v3.base import listens
from ableton.v3.control_surface import ControlSurface, ControlSurfaceSpecification, create_skin
from ableton.v3.control_surface.capabilities import AUTO_LOAD_KEY, CONTROLLER_ID_KEY, NOTES_CC, PORTS_KEY, SCRIPT, SYNC, controller_id, inport, outport
from ableton.v3.control_surface.components import DEFAULT_DRUM_TRANSLATION_CHANNEL, MixerComponent
from  import midi
from colors import Rgb
from display import display_specification
from display_status import DisplayStatusComponent
from elements import CONTINUOUS_PARAMETER_SENSITIVITY, Elements
from legacy import LegacyComponent
from mappings import create_mappings
from session import SessionComponent
from skin import Skin

def get_capabilities():
    return {
        AUTO_LOAD_KEY: True,
        PORTS_KEY: [
            inport(props = []),
            inport(props = [
                SCRIPT,
                NOTES_CC]),
            outport(props = []),
            outport(props = [
                SCRIPT,
                SYNC])],
        CONTROLLER_ID_KEY: controller_id(vendor_id = 2536, product_ids = [
            93], model_name = [
            'MPK mini IV']) }


def create_instance(c_instance):
    return MPK_mini_IV(specification = Specification, c_instance = c_instance)


class Specification(ControlSurfaceSpecification):
    elements_type = Elements
    control_surface_skin = create_skin(skin = Skin, colors = Rgb)
    identity_response_id_bytes = (71, 93, 0, 25)
    hello_messages = (midi.make_message(midi.MAIN_MODE_MESSAGE_ID),)
    goodbye_messages = (midi.make_message(midi.PADS_TO_PORT_1_MESSAGE_ID, 0),)
    create_mappings_function = create_mappings
    display_specification = display_specification
    num_tracks = 4
    num_scenes = 4
    link_session_ring_to_track_selection = True
    link_session_ring_to_scene_selection = True
    continuous_parameter_sensitivity = CONTINUOUS_PARAMETER_SENSITIVITY
    quantized_parameter_sensitivity = 0.2
    feedback_channels = [
        DEFAULT_DRUM_TRANSLATION_CHANNEL]
    playing_feedback_velocity = Rgb.GREEN.midi_value
    recording_feedback_velocity = Rgb.RED.midi_value
    component_map = {
        'Display_Status': DisplayStatusComponent,
        'Legacy': LegacyComponent,
        'Mixer_2': MixerComponent,
        'Session_2': SessionComponent }


class MPK_mini_IV(ControlSurface):
    pass
# WARNING: Decompyle incomplete
