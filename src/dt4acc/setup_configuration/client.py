from p4p.client.thread import Context
import time


# Function to read PV values
def read_pv(pv_name):
    # Create a context to connect to the PV
    ctxt = Context('pva')

    # Read the value of the PV
    value = ctxt.get(pv_name)

    # Print the value
    print(f"{pv_name}: {value}")


# Main function
def main():
    # List of PV names (replace with the actual PV names you've created)
    pv_names = ["Pierre:DT:Q4M2D1R", 'Pierre:DT:S3M2D1R']  # Example PV names

    # Read values from each PV in a loop
    while True:
        for pv_name in pv_names:
            read_pv(pv_name)
        time.sleep(1)  # Wait for 1 second before reading again


if __name__ == "__main__":
    main()
