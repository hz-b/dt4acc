import logging
import os.path
import json
import time
import threading
import pydev

# logging.basicConfig(level=logging.DEBUG)
logger = logging.Logger("thor-scsi-lib")
logger.setLevel(logging.WARNING)
mux_off = "Mux OFF"


class Muxer:
    """Muxer implementation for digital twin

    Todo:
        make the delay settable
    """

    def __init__(self, *, selected=None, positive_list, prefix):
        # import epics

        self._selected = selected
        self._positive_list = positive_list
        self._prefix = prefix

        self._running = False

    def _redirectRelay(self):
        """Set the correct out value to the calcout variable


        Todo:
            Implement a test if the muxer set the current back to
            zero.
        """
        for name in self._positive_list:
            # Todo: get machine names to upper names
            name = name.lower()
            label = f"{self._prefix}:{name}:im:mux:active"
            if self._selected is not None and name == self._selected:
                logger.info(f"Selected {label}")
                flag = True
            else:
                flag = False

            logger.debug(f"MUXER {label}: selected? {flag}")
            pydev.iointr(label, flag)

    def off(self, val):
        """Switch muxer off ....

        Todo:

            which value is off?
        """
        self._selected = None
        self._redirectRelay()
        self.setDisplayName(mux_off)

    def setDisplayName(self, name):
        pydev.iointr("muxer_selected_magnet", name)

    def select(self, a_list):
        """

        Todo:
            Check that the selected name is on a positive list.
        """

        name, val = a_list

        if val == 2:
            logger.info("Processing undefined value (typically from init)")

        # if self._running:
        #    logger.error(f"How called when already running? name {name}")

        self._running = True

        # Book keeping for how the muxer responds
        if self._selected is None:
            # Muxer was off before
            was_off = True
        else:
            was_off = False

        if self._selected == name:
            # This magnet was already selected by the muxer
            already_selected = True
        else:
            already_selected = False

        if not val:
            logger.info(f"Disabling muxer as val {val}: not checking name {name}")
            self._selected = None
        else:
            if name not in self._positive_list:
                logger.error(f"Muxer: selected name  {name} not in positive list!")
                self._selected = None
            else:
                self._selected = name

        # create appropriate relay variable

        if val:
            display_name = name
            logger.info(f"Muxer selected magnet {name} :  value {val}")
        else:
            display_name = mux_off

        # Longer delay if value is set ... be closer to the real device
        # At startup this routine is called many times. Be rather fast
        # here so that startup finishes swiftly
        if val:
            delay = 1e-2
        else:
            delay = 1e-3

        # Some states require to emit more than one value. These have to
        # be emitted in a separate thraad so that other records can react
        # First lambda functions are defined then the
        # thread is start up
        def signal_name(name, state):
            logger.info(f'Muxer display name "{name}" state "{state}"')
            self.setDisplayName(name)

        def fend():
            # Now switching virtual relay ....
            self._redirectRelay()
            self._running = False
            logger.info(f"Muxer processing: {display_name} done")

        def fwas_off():
            state = was_off
            signal_name(display_name, state)
            time.sleep(delay)
            signal_name(mux_off, state)
            time.sleep(delay)
            signal_name(display_name, state)
            fend()

        def falready_selected():
            signal_name(display_name, "already selected")
            fend()

        def fswitch_to_other_magnet():
            logger.info("Switching from one magnet to an other one")
            # On but an other device was selected
            signal_name(mux_off, "switching")
            time.sleep(delay)
            signal_name(display_name, "switching")
            fend()

        logger.info(
            f"Muxer processing: was off {was_off} already_selected {already_selected} delay {delay}"
        )
        # That's how the muxer responds ....
        # according to the comment in the description
        if was_off:
            func = fwas_off
        elif already_selected:
            func = falready_selected
        else:
            func = fswitch_to_other_magnet

        thread = threading.Thread(target=func)
        thread.start()

    def __repr__(self):
        cls_name = self.__class__.__name__
        txt = f"{cls_name}(selected={self._selected})"
        return txt


def build_muxer(*, prefix, positive_list_file="quadrupole_names.json"):
    # Get list of magnets
    quad_names_file = os.path.join("db", positive_list_file)
    with open(quad_names_file) as fp:
        quad_names = json.load(fp)

    quad_names = [name.upper() for name in quad_names]
    mux = Muxer(positive_list=quad_names, prefix=prefix)
    return mux
