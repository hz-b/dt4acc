import pandas as pd


def main():
    df = pd.read_csv("sextupole_sorting.txt", header=None, sep='\s+')
    df.columns = ["location_name", "device_name"]
    df = df.set_index("location_name").sort_values("device_name")
    print(df.shape)
    params = {
        "SX13443": {
            "A": 0.5196,
            "B": 0.49524,
            "D": -4.45E-12
        },
        "SX13444": {
            "A": 0.4824,
            "B": 0.49512,
            "D": -4.22E-12
        },
        "SX13445": {
            "A": 0.5196,
            "B": 0.49512,
            "D": -4.39E-12
        },
        "SX13447": {
            "A": 0.6714,
            "B": 0.63048,
            "D": -4.17E-12
        }
    }

    # need to write
    # { "SX13447:02",  "S1MT4R",          0.6714,             0.63048,                -4.17E-12       }
    for location, item in df.iterrows():
        device_name = item.device_name.replace('#', ":")
        generic_device_name, device_number = device_name.split(":")
        # print(location, device_name)
        txt = f'\t{{ "{device_name}",     "{location}", \t\t"{params[generic_device_name]["A"]}", \t\t"{params[generic_device_name]["B"]}",  \t\t"{params[generic_device_name]["D"]}" }}'
        print(txt)


if __name__ == '__main__':
    main()
