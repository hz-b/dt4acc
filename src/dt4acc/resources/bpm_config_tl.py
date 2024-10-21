
#: Data of the beam positon monitors. It is a list of tuples.
#: Each tuple contains:
#:    * `bpm name`
#:    * `x state`: boolean (?)
#:    * `y state`: boolean (?)
#:    * `ds:`       longitudinal position in the machine ds = 0 : injection point
#:    * `idx:`      index for this bpm data in bdata/packed_data
#:    * `scale x`:  fixed scaling data for converting raw data to millimeter
#:    * `scale y`:  fixed scaling data for converting raw data to millimeter
#:
bpm_conf = [
    #: BPM        X/Y-State   ds             idx    scaleX     scaleY
    ("FOMZ1T",    0, 0,     0,             2,      1,         1),
    ("FOMZ2T",    0, 0,     0,             6,      1,         1),
    ("BPMZ1T",    0, 0,     0,             8,      1,         1),
    ("SLZ1T",     0, 0,     0,            15,      1,         1),
    ("SLZ2T",     0, 0,     0,            19,      1,         1),
    ("FOMZ3T",    0, 0,     0,            23,      1,         1),
    ("BPMZ2T",    0, 0,     0,            25,      1,         1),
    ("FOMZ4T",    0, 0,     0,            32,      1,         1),
    ("BPMZ3T",    0, 0,     0,            34,      1,         1),
    ("FOMZ5T",    0, 0,     0,            49,      1,         1),
    ("BPMZ4T",    0, 0,     0,            51,      1,         1),
    ("FOMZ6T",    0, 0,     0,            62,      1,         1),
    ("BPMZ5T",    0, 0,     0,            64,      1,         1),
    ("FOMZ7T",    0, 0,     0,            78,      1,         1),
    ("SLZ3T",     0, 0,     0,            84,      1,         1),
    ("FOMZ8T",    0, 0,     0,            86,      1,         1),
    ("FOMZ2D1R",  0, 0,     0,            92,      1,         1)
]

#: offsets of the Beam position monitors
#: in millimeter
bpm_offset = {
    "FOMZ1T":   (0.0,  0.0),
    "FOMZ2T":   (0.0,  0.0),
    "BPMZ1T":   (0.0,  0.0),
    "SLZ1T":    (0.0,  0.0),
    "SLZ2T":    (0.0,  0.0),
    "FOMZ3T":   (0.0,  0.0),
    "BPMZ2T":   (0.0,  0.0),
    "FOMZ4T":   (0.0,  0.0),
    "BPMZ3T":   (0.0,  0.0),
    "FOMZ5T":   (0.0,  0.0),
    "BPMZ4T":   (0.0,  0.0),
    "FOMZ6T":   (0.0,  0.0),
    "BPMZ5T":   (0.0,  0.0),
    "FOMZ7T":   (0.0,  0.0),
    "SLZ3T":    (0.0,  0.0),
    "FOMZ8T":   (0.0,  0.0),
    "FOMZ2D1R": (0.0,  0.0)
}
