class LatticeElementPropertyID:
    """Identifier for lattice element properties."""
    
    def __init__(self, element_name: str, property: str):
        self.element_name = element_name
        self.property = property

class DevicePropertyID:
    """Identifier for device properties."""
    
    def __init__(self, device_name: str, property: str):
        self.device_name = device_name
        self.property = property 