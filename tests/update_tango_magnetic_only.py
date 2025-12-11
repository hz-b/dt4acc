

from tango import Database


def main() -> None:
    db = Database()
    devices = db.get_device_name("*", "*")  # all devices in the DB

    removed = 0
    for dev in devices:
        try:
            db.delete_device(dev)
            print(f"Deleted {dev}")
            removed += 1
        except Exception as exc:
            print(f"Failed to delete {dev}: {exc}")

    print(f"Total removed: {removed}")


if __name__ == "__main__":
    main()