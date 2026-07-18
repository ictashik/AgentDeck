# Decompiled with pycdc from Ableton Live 12 (Python 3.11).
# Some functions may be partial: pycdc cannot fully decompile 3.11 bytecode.

# Source Generated with Decompyle++
# File: colors.pyc (Python 3.11)

from ableton.v3.base import memoize
from ableton.v3.control_surface.elements import FallbackColor, SimpleColor
from ableton.v3.control_surface.midi import NOTE_ON_STATUS
from ableton.v3.live import liveobj_valid
from  import midi
make_simple_color = (lambda value: SimpleColor(value))()

def make_color_for_liveobj(obj):
    pass
# WARNING: Decompyle incomplete


class UIButtonColor(SimpleColor):
    
    def draw(self, interface):
        interface.send_midi((NOTE_ON_STATUS + self._channel, interface.message_identifier(), self._value))



class Basic:
    FULL = UIButtonColor(127, channel = midi.FULL_BRIGHTNESS_LED_CHANNEL)
    HALF = UIButtonColor(1, channel = midi.HALF_BRIGHTNESS_LED_CHANNEL)
    BLINK = UIButtonColor(127, channel = midi.BLINK_LED_CHANNEL)


class Rgb:
    OFF = FallbackColor(make_simple_color(0), Basic.HALF)
    GREY = make_simple_color(1)
    WHITE = make_simple_color(3)
    RED = make_simple_color(5)
    RED_HALF = SimpleColor(5, channel = midi.HALF_BRIGHTNESS_LED_CHANNEL)
    RED_BLINK = SimpleColor(5, channel = midi.BLINK_LED_CHANNEL)
    RED_PULSE = SimpleColor(5, channel = midi.PULSE_LED_CHANNEL)
    AMBER = make_simple_color(9)
    GREEN = make_simple_color(21)
    GREEN_HALF = SimpleColor(21, channel = midi.HALF_BRIGHTNESS_LED_CHANNEL)
    GREEN_BLINK = SimpleColor(21, channel = midi.BLINK_LED_CHANNEL)
    GREEN_PULSE = SimpleColor(21, channel = midi.PULSE_LED_CHANNEL)
    BLUE = make_simple_color(45)

# WARNING: Decompyle incomplete
