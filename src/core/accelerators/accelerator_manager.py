from src.core.utils.logger import get_logger
from src.custom_epics.utils.bpm_mimicry import BPMMimicry
from .proxy_factory import PyATProxyFactory
from ..accelerators.accelerator_impl import AcceleratorImpl
from ..calculations.pyat_calculator import PyAtTwissCalculator, PyAtOrbitCalculator
from ...custom_epics.views.shared_view import get_view_instance

logger = get_logger()


class AcceleratorManager:
    """
    Manages the initialization and event subscription of the accelerator.
    Orchestrates interactions, manages configurations,
    and serves as a bridge between core accelerator logic and higher-level application needs.

    Attributes:
        prefix (str): The prefix for PVs (Process Variables).
        accelerator (AcceleratorImpl): Instance of the accelerator implementation.
        view (ResultView): Instance of the result view to handle user interface.
        bpm_mimicry (BPMMimicry): Object to manage BPM data mimicking.
    """

    def __init__(self, prefix):
        """
        Initializes the AcceleratorManager with a given prefix.

        Args:
            prefix (str): The prefix for the PVs in the EPICS system.
            todo: What about tango? do we have/need usage of prefix? we will findout
        """
        self.prefix = prefix
        self.accelerator = None  # Will be initialized in the `initialize` method
        self.view = get_view_instance()  # Shared view instance for displaying results
        self.bpm_mimicry = None  # Placeholder for BPM mimicry instance

    def initialize(self):
        """
        Initializes the accelerator and its required components.

        This method sets up the accelerator, proxies, calculators, and BPMs.
        It also subscribes to relevant events.

        Raises:
            Exception: If initialization fails.
        """
        try:
            from lat2db.model.accelerator import Accelerator
            acc_model = Accelerator()

            # Initialize the accelerator with required components
            self.accelerator = AcceleratorImpl(
                acc_model.ring,
                PyATProxyFactory(lattice_model=None, at_lattice=acc_model.ring),
                PyAtTwissCalculator(acc_model),
                PyAtOrbitCalculator(acc_model.ring)
            )

            # Extract BPM elements from the accelerator and create BPM mimicry
            bpm_names = [elem.FamName for elem in self.accelerator.acc if elem.FamName.startswith("BPM")]
            self.bpm_mimicry = BPMMimicry(prefix=self.prefix, bpm_names=bpm_names)
            # Inject the BPM mimicry into the view instance
            self.view.set_bpm_mimicry(self.bpm_mimicry)
            self.setup_event_subscriptions()

            logger.warning("AcceleratorManager initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize AcceleratorManager: {e}")
            raise

    def setup_event_subscriptions(self):
        """
        Subscribe to accelerator events and bind them to view update methods.

        Ensures that the view receives updates whenever the accelerator produces new data.
        """
        if not self.accelerator:
            logger.error("Accelerator must be initialized before subscribing to events.")

        # Subscriptions
        self.accelerator.on_new_twiss.subscribe(self.view.push_twiss)
        self.accelerator.on_new_orbit.subscribe(self.view.push_orbit)

        self.accelerator.on_new_orbit.subscribe(self.view.push_bpms)
        self.accelerator.on_changed_value.subscribe(self.view.push_value)
