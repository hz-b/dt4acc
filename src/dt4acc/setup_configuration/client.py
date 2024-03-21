from p4p.client.thread import Context


def read_pv(pv_name, ctx):
    value = ctx.get(pv_name)
    print(f"{pv_name}: {value}")


def write_pv(pv_name, new_value, ctx):
    ctx.put(pv_name, new_value)


def main():
    pv_names = ["Pierre:DT:Q4M2D1R"]
    # Create a context to connect to the PV
    ctx = Context('pva')
    # Write values to each PV in a loop
    for pv_name in pv_names:
        write_pv(pv_name, 5, ctx)
    # while True:
    #     for pv_name in pv_names:
    #         read_pv(pv_name, ctx)
        # time.sleep(1)  # Wait for 1 second before reading again


if __name__ == "__main__":
    main()
