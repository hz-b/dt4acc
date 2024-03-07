import cothread
from dt4acc.resources.bessy2_sr_reflat import bessy2Lattice
from p4p.nt import NTScalar
from p4p.server import Server
from p4p.server.cothread import SharedPV


# Define a handler class for handling write requests to the PV
class ElementHandler(object):
    def __init__(self, element):
        self.element = element

    def put(self, pv, op):
        # this will be an update of the element
        # Respond to the write request
        op.done()


# Function to create shared PVs for each element in the accelerator list
def create_shared_pv(element):
    # Create a shared PV for the element
    # Construct NTScalarArray object for the element with an array of zeros as the initial value
    initial_value = [0.0] * 128  # Adjust array_length to the desired length of the array
    nt_data = NTScalar('ad')
    nt_data.wrap(initial_value)
    pv = SharedPV(nt=NTScalar('ad'),
                  initial=initial_value,
                  handler=ElementHandler(element))
    return pv


# Iterate over each element in the accelerator list and create shared PVs
ring_pvs = {}

acc = bessy2Lattice()
prefix = "Pierre:DT:"
for element in acc:
    element_str = str(element)
    element_split_by_space = element_str.split('\n')
    element_type = element_split_by_space[0]
    if element_type in ["Quadrupole:", "Sextupole:", "Dipole:"]:
        pv_name = prefix + element.FamName
        ring_pvs[pv_name] = create_shared_pv(element)

# Create a P4P server with the created shared PVs
with Server(providers=[ring_pvs]):
    print('Server Starting')
    try:
        cothread.WaitForQuit()
    except KeyboardInterrupt:
        pass
