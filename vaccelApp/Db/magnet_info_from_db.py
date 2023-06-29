from pymongo import MongoClient
import pandas as pd
import numpy as np
from bact_math_utils.misc import CountSame
import os.path
import json

c_dir = os.path.join(os.path.dirname(__file__))

# Set to none for now limit
max_lines = None


def setpoint_2_power_converter_name(pvname: str) -> str:
    """
    """

    pc, t_set = pvname.split(":")
    t_set = t_set.strip()
    if t_set != "set":
        txt = f'pvname {pvname} does not end in ":set": "{pc}", "{t_set}"'
        raise AssertionError(txt)

    return pc


def sector_gen(names):
    for name in names:
        name = name.strip()
        yield name[3:-3]


def straight_gen(names):
    for name in names:
        name = name.strip()
        yield name[-3]


def magnet_family(names):
    for name in names:
        name = name.strip()
        if len(name) == 7:
            yield "."
        else:
            yield name[:3]


def generate_lines(df, *, pos_names, entry_types):
    mag_fam = CountSame()(magnet_family(pos_names))
    sec = CountSame()(sector_gen(pos_names))
    straight = CountSame()(straight_gen(pos_names))

    yield f"#start of {entry_types}"

    line_intend = "\t\t"
    first = True
    for cnt, tmp in enumerate(zip(df.iterrows(), mag_fam, sec, straight)):
        if max_lines is not None and cnt > max_lines:
            break

        ir, mag_fam, n_sec, n_straight = tmp
        index, row = ir
        add_comment_line = False
        if not first:
            if mag_fam[0] == 0:
                yield ""
            if n_sec[0] == 0:
                add_comment_line = True
                yield ""
            if n_straight[0] == 0:
                yield ""

        first = False

        if add_comment_line:
            yield f"# {mag_fam[1]}{n_sec[1]}{n_straight[1]}"

        yield line_intend + "{{ {} }} ".format(", ".join([str(tmp) for tmp in row]))

    yield f"# end of {entry_types}"


def create_fanout(single, elements):
    assert len(elements) <= 16
    elements = list(elements)[:]
    elements.sort()
    links = [
        f'field(LNK{cnt:X}, "$(PREFIX):{element}:im:I")'
        for cnt, element in enumerate(elements)
    ]
    links_txt = "\n".join([f"    {item}" for item in links])
    txt = f"""record(fanout, "$(PREFIX):{single}:dt:fanout")
{{
    field(DESC, "informing further elements")
{links_txt}
}}
    """
    return txt


def load_data(collection_names, index_name=None):
    def col2df(collection_name):
        collection = getattr(db, collection_name)
        df = pd.DataFrame(collection.find())

        if index_name is not None:
            df = df.set_index(index_name)
        return df

    host = "mongodb.bessy.de"
    # host = "localhost"
    port = 37017
    url = f"mongodb://visitor:HZB@{host}:{port}/"
    with MongoClient(url) as client:
        db = client.BESSY2
        dfs = [col2df(name) for name in collection_names]
        return dfs


# Load data for the steerers
df_vcm, = load_data(["StorageRing.VCM"])
df_vcm.reindex(columns=list(df_vcm.columns) + ["element", "default_current", "PS"])
df_vcm = df_vcm.loc[[name[:3] != "VS4" for name in df_vcm.CommonNames], :]
df_vcm.loc[:, "PS"] = df_vcm.Setpoint.apply(setpoint_2_power_converter_name)
df_vcm.loc[:, "polarity"] = np.where(df_vcm.hw2phys < 0, -1, 1)
df_vcm.loc[:, "default_current"] = 0.0
df_vcm.loc[:, "element"] = [name.lower() for name in df_vcm.CommonNames.values]


df_hcm, = load_data(["StorageRing.HCM"])
df_hcm.reindex(columns=list(df_hcm.columns) + ["element", "default_current", "PS"])
df_hcm.loc[:, "PS"] = df_hcm.Setpoint.apply(setpoint_2_power_converter_name)
df_hcm.loc[:, "polarity"] = np.where(df_hcm.hw2phys < 0, -1, 1)
# Ignore the ones on the dipoles
df_hcm = df_hcm.loc[[name[:2] != "HB" for name in df_hcm.CommonNames], :]
df_hcm.loc[:, "default_current"] = 0.0
df_hcm.loc[:, "element"] = [name.lower() for name in df_hcm.CommonNames.values]

# Quadrupoles
df_qs = load_data(
    [
        "StorageRing.Q1",
        "StorageRing.Q2",
        "StorageRing.Q3",
        "StorageRing.Q4",
        "StorageRing.Q5",
    ]
)
df_q = pd.concat(df_qs)
df_q.reindex(columns=list(df_q.columns) + ["element", "default_current", "PS"])
df_q.loc[:, "PS"] = df_q.Setpoint.apply(setpoint_2_power_converter_name)
df_q.loc[:, "element"] = [name.lower() for name in df_q.CommonNames]

# Only these power converters have currently default values
# all others would spoil the settings from the lattice file
# df_q = df_q.loc[(df_q.PS == "Q1PDR") | (df_q.PS == "Q1PTR")]

# data as measured by loco
df_quad_loco = pd.read_json("bessy2_quad_loco_current_hw2phys.json")

# Export steerer fanout ... steerer dt power converter to element
# power converter
# Quadrupoles have many on one line ... created differently.
# Here it is one to one so I use a template to create them


def dt2Lines(df: pd.DataFrame, *, columns: list, entry_type: str):
    """
    """
    df = df.sort_values("CommonNames")
    gen = generate_lines(
        df.loc[:, columns], pos_names=df.element.values, entry_types=entry_type
    )
    return list(gen)


hcm_lines = dt2Lines(
    df_hcm, columns=["PS", "element"], entry_type="horizontal_steerers"
)
vcm_lines = dt2Lines(df_vcm, columns=["PS", "element"], entry_type="vertical_steerers")
q_lines = dt2Lines(df_q, columns=["PS", "element"], entry_type="quadrupoles")

txt = "\n".join(
    ["file db/power_converter_relay.rec", "{", "\tpattern {PC, ELEMENT}"]
    + q_lines
    + ["", ""]
    + hcm_lines
    + ["", ""]
    + vcm_lines
    + ["}", "# EOF", ""]
)
filename = os.path.join(c_dir, "power_converter_relay.inc")
with open(filename, "wt") as fp:
    fp.write(txt)

print(df_vcm.columns)
df_vcm.loc[:, ["PS", "element", "CommonNames"]].to_json("vertical_steerers.json", indent=4)
df_hcm.loc[:, ["PS", "element", "CommonNames"]].to_json("horizontal_steerers.json", indent=4)
#df_hcm.to_json("horizontal_steerers.json", ident=4)

txt = "\n".join(
    ["file db/power_converter_fanout.rec", "{", "\tpattern {PC, ELEMENT}"]
    + hcm_lines
    + ["", ""]
    + vcm_lines
    + ["}", "# EOF", ""]
)
filename = os.path.join(c_dir, "power_converter_fanout.inc")
with open(filename, "wt") as fp:
    fp.write(txt)

# Quadrupole power converters are many to many
power_converters = list(set(df_q.PS))
power_converters.sort()
fanouts = [
    create_fanout(ps, df_q.loc[df_q.PS == ps, "element"]) for ps in power_converters
]
txt = "\n".join(fanouts + ["# EOF", ""])
filename = os.path.join(c_dir, "quadrupole_power_converter_fanout.inc")
with open(filename, "wt") as fp:
    fp.write(txt)


# Create virtual instances so that muxer can inform the Imux
# that is connected
# power_converter_relay expects Imux to be found for every single elment
# thus a few records never to be used
hcm_lines = dt2Lines(df_hcm, columns=["element"], entry_type="horizontal_steerers")
vcm_lines = dt2Lines(df_vcm, columns=["element"], entry_type="vertical_steerers")
q_lines = dt2Lines(df_q, columns=["element"], entry_type="quadrupoles")
txt = "\n".join(
    ["file db/muxer_elements.rec", "{", "\tpattern\t {ELEMENT }"]
    + q_lines
    + ["", ""]
    + hcm_lines
    + ["", ""]
    + vcm_lines
    + ["}", "# EOF", ""]
)
filename = os.path.join(c_dir, "muxer_elements.inc")
with open(filename, "wt") as fp:
    fp.write(txt)


# Now the hardware translation
df = df_hcm.sort_values("CommonNames")
hcm_lines = list(
    generate_lines(
        df.loc[:, ["element", "hw2phys"]],
        pos_names=df.element.values,
        entry_types="horizontal correctors",
    )
)

df = df_vcm.sort_values("CommonNames")
vcm_lines = list(
    generate_lines(
        df.loc[:, ["element", "hw2phys"]],
        pos_names=df.element.values,
        entry_types="vertical correctors",
    )
)

df = df_q.sort_values("CommonNames")
df_quad_loco2 = df_quad_loco.reindex(columns=list(df_quad_loco.columns) + ["element"])
df_quad_loco2.loc[:, "element"] = [name.lower() for name in df_quad_loco.index.values]
q_lines = list(
    generate_lines(
        # df.loc[:, ["element", "hw2phys"]],
        # In this case ... also write power_converter currents
        df_quad_loco2.loc[:, ["element", "hw2phys"]],
        pos_names=df_quad_loco2.element.values,
        entry_types="quadrupoles",
    )
)

txt = "\n".join(
    ["file db/transfer_function.rec", "{", "\tpattern {ELEMENT, HW2PHYS}"]
    + q_lines
    + ["", ""]
    + hcm_lines
    + ["", ""]
    + vcm_lines
    + ["}", "# EOF", ""]
)

filename = os.path.join(c_dir, "transfer_function.inc")
with open(filename, "wt") as fp:
    fp.write(txt)



# Default currents
# Now the hardware translation
df = df_hcm.sort_values("CommonNames")
hcm_lines = list(
    generate_lines(
        df.loc[:, ["PS", "default_current"]],
        pos_names=df.element.values,
        entry_types="horizontal correctors",
    )
)

df = df_vcm.sort_values("CommonNames")
vcm_lines = list(
    generate_lines(
        df.loc[:, ["PS", "default_current"]],
        pos_names=df.element.values,
        entry_types="vertical correctors",
    )
)
"\n".join(vcm_lines)

# Connected to more than one magnet sometimes ... reduce it to them
df_quad_loco_red = df_quad_loco.loc[:, ["setpoint", "current"]]
quad_power_converter_names = list(set(df_quad_loco_red.setpoint.values))
# QIPTR ...
quad_power_converter_names.remove(None)
quad_power_converter_names.sort()
# should be identical for different lines here one should suffice
tmp = list(df_quad_loco_red.setpoint.values)
quad_sel_idx = [tmp.index(name) for name in quad_power_converter_names]
df_quad_loco_red = df_quad_loco_red.iloc[quad_sel_idx, :]
q_lines = list(
    generate_lines(
        # df.loc[:, ["element", "hw2phys"]],
        # In this case ... also write power_converter currents
        df_quad_loco_red.loc[:, ["setpoint", "current"]],
        # pos_names=df.element.values,
        pos_names=df_quad_loco_red.setpoint.values,
        entry_types="quadrupoles",
    )
)

txt = "\n".join(
    ["file db/power_converter.rec", "{", "\tpattern {PC, DEFAULT_CURRENT}"]
    + hcm_lines
    + ["", ""]
    + vcm_lines
    + ["", ""]
    + q_lines
    + ["}", "# EOF", ""]
)
filename = os.path.join(c_dir, "power_converter.inc")
with open(filename, "wt") as fp:
    fp.write(txt)



q_lines = list(
    generate_lines(
        # df.loc[:, ["element", "hw2phys"]],
        # In this case ... also write power_converter currents
        df_quad_loco2.loc[:, ["element"]],
        # pos_names=df.element.values,
        pos_names=df_quad_loco2.element,
        entry_types="quadrupoles",
    )
)

txt = "\n".join(
    ["file db/offset.rec", "{", "\tpattern {ELEMENT}"]
    + q_lines
    + ["}", "# EOF", ""]
)
filename = os.path.join(c_dir, "offset.inc")
with open(filename, "wt") as fp:
    fp.write(txt)

df = df_q.sort_values("CommonNames")
quadrupole_names = list(df.element.values)
quadrupole_names.sort()

with open("quadrupole_names.json", "w") as fp:
    json.dump(quadrupole_names, fp, indent=True)
