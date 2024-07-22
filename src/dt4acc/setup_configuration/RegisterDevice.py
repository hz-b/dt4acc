from tango import Database, DbDevInfo


def register_device(device_names, domain="DT"):
    db = Database()

    dev_info = DbDevInfo()
    dev_info.name = f"{domain}/bpm/bdata"
    dev_info._class = "MyTangoDevice"
    dev_info.server = f"MyTangoDevice/DT"
    db.add_device(dev_info)
    for name in device_names:
        dev_info = DbDevInfo()
        dev_info.name = f"{domain}/{name}/cm"
        dev_info._class = "MyTangoDevice"
        dev_info.server = f"MyTangoDevice/DT1"
        db.add_device(dev_info)


if __name__ == "__main__":
    from lat2db.model.accelerator import Accelerator

    acc = Accelerator().machine.sequences
    device_names = [element.name for element in acc if element.type in ["Sextupole", "Quadrupole"]]
    register_device(device_names)

    print("Devices registered successfully!")
