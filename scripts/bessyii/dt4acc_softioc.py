import logging
logging.basicConfig(level=logging.WARNING)

from softioc import builder, softioc

from accml.core.utils.basic_measurement_execution_engine import BasicMeasurementExecutionEngine
from accml_lib.core.bl.command_rewritter import CommandRewriter
from accml_lib.core.model.utils.command import ReadCommand
from accml_lib.core.model.utils.identifiers import DevicePropertyID, ConversionID
from accml_lib.custom.bessyii.liasion_translator_setup import load_managers
from dt4acc.core.accelerators.pyat_accelerator import setup_accelerator
from dt4acc.custom_epics.ioc.server import View, Controller, dispatcher


def main():
    # Start the IOC server by dispatching the main function
    _, lm, ts = load_managers()

    print(lm)
    print(ts)
    # print(repr(ts))

    # Just for test
    dev_p = DevicePropertyID(device_name="tune", property="transversal_frequency")
    dev_p = DevicePropertyID(device_name="tune", property="transversal")
    lat_p, = lm.inverse(dev_p)
    test = ts.get(ConversionID(lat_p, dev_p))
    test

    command_rewriter=CommandRewriter(
        liaison_manager=lm,
        translation_service=ts
    )
    # Todo: review if a dedicated execution engine
    #       View gets an engine to execute
    #       each trigger calls to the engine. When something happens
    mexec = BasicMeasurementExecutionEngine(
        backend=setup_accelerator(),
        cmd_rewriter=command_rewriter,
        storage=None,
        expected_view_for_output="device",
        num_readings=1,
    )
    # Todo: should be rather a controller
    view = View()
    controller = Controller(
        view=view,
        mexec=mexec,
        builder=builder,
        default_delayed_reads=[
            ReadCommand("track", "pos"),
            ReadCommand("twiss", "parameters"),
            ReadCommand("tune", "x"),
            ReadCommand("tune", "y"),
        ]
    )
    dispatcher(controller.startup)
    # Start the interactive IOC shell, allowing interaction with the server
    softioc.interactive_ioc(globals())


if __name__ == "__main__":
    main()
