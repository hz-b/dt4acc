"""
Knowledge Base for Tango AI Agent
Contains comprehensive knowledge about Tango devices, commands, and operations
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class DeviceSchema:
    """Schema for a Tango device"""
    name: str
    type: str
    class_name: str
    description: str
    attributes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    commands: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    safety_limits: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)

@dataclass
class CommandTemplate:
    """Template for a command"""
    name: str
    description: str
    natural_language: List[str]
    tango_command: str
    parameters: Dict[str, Dict[str, Any]]
    examples: List[str]
    safety_notes: List[str]

@dataclass
class TangoKnowledgeBase:
    """Comprehensive knowledge base for Tango operations"""
    
    def __init__(self, base_path: str = "knowledge_base"):
        self.base_path = Path(base_path)
        self.devices: Dict[str, DeviceSchema] = {}
        self.commands: Dict[str, CommandTemplate] = {}
        self.device_types: Dict[str, List[str]] = {}
        self.safety_rules: Dict[str, Any] = {}
        self.operation_modes: Dict[str, Any] = {}
        
        # Load knowledge base
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """Load all knowledge base components"""
        try:
            self._load_device_schemas()
            self._load_command_templates()
            self._load_safety_rules()
            self._load_operation_modes()
            logger.info("Knowledge base loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            self._create_default_knowledge_base()
    
    def _load_device_schemas(self):
        """Load device schemas from files"""
        schemas_path = self.base_path / "schemas" / "devices"
        if not schemas_path.exists():
            return
        
        for schema_file in schemas_path.glob("*.yaml"):
            try:
                with open(schema_file, 'r') as f:
                    data = yaml.safe_load(f)
                    schema = DeviceSchema(**data)
                    self.devices[schema.name] = schema
                    
                    # Index by device type
                    if schema.type not in self.device_types:
                        self.device_types[schema.type] = []
                    self.device_types[schema.type].append(schema.name)
                    
            except Exception as e:
                logger.error(f"Failed to load device schema {schema_file}: {e}")
    
    def _load_command_templates(self):
        """Load command templates from files"""
        templates_path = self.base_path / "templates" / "commands"
        if not templates_path.exists():
            return
        
        for template_file in templates_path.glob("*.yaml"):
            try:
                with open(template_file, 'r') as f:
                    data = yaml.safe_load(f)
                    template = CommandTemplate(**data)
                    self.commands[template.name] = template
                    
            except Exception as e:
                logger.error(f"Failed to load command template {template_file}: {e}")
    
    def _load_safety_rules(self):
        """Load safety rules"""
        safety_file = self.base_path / "safety" / "rules.yaml"
        if safety_file.exists():
            try:
                with open(safety_file, 'r') as f:
                    self.safety_rules = yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Failed to load safety rules: {e}")
    
    def _load_operation_modes(self):
        """Load operation modes"""
        modes_file = self.base_path / "operations" / "modes.yaml"
        if modes_file.exists():
            try:
                with open(modes_file, 'r') as f:
                    self.operation_modes = yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Failed to load operation modes: {e}")
    
    def _create_default_knowledge_base(self):
        """Create default knowledge base with built-in knowledge"""
        logger.info("Creating default knowledge base")
        
        # Default device schemas
        self.devices = {
            "power_converter": DeviceSchema(
                name="power_converter",
                type="power_converter",
                class_name="PowerConverterDevice",
                description="Power converter device for controlling magnet currents",
                attributes={
                    "current": {
                        "type": "float",
                        "unit": "A",
                        "description": "Current value",
                        "readable": True,
                        "writable": False
                    },
                    "current_setpoint": {
                        "type": "float",
                        "unit": "A",
                        "description": "Current setpoint",
                        "readable": True,
                        "writable": True
                    },
                    "voltage": {
                        "type": "float",
                        "unit": "V",
                        "description": "Voltage value",
                        "readable": True,
                        "writable": False
                    },
                    "voltage_setpoint": {
                        "type": "float",
                        "unit": "V",
                        "description": "Voltage setpoint",
                        "readable": True,
                        "writable": True
                    },
                    "status": {
                        "type": "string",
                        "description": "Device status",
                        "readable": True,
                        "writable": False
                    }
                },
                safety_limits={
                    "current": {"min": 0.0, "max": 1000.0, "unit": "A"},
                    "voltage": {"min": 0.0, "max": 100.0, "unit": "V"}
                },
                examples=[
                    "Set Q3P2T6R current to 5.1A",
                    "Get Q3P2T6R current setpoint",
                    "List all power converters"
                ]
            ),
            "quadrupole": DeviceSchema(
                name="quadrupole",
                type="quadrupole",
                class_name="QuadrupoleDevice",
                description="Quadrupole magnet for beam focusing",
                attributes={
                    "strength": {
                        "type": "float",
                        "unit": "1/m",
                        "description": "Quadrupole strength",
                        "readable": True,
                        "writable": True
                    },
                    "k_strength": {
                        "type": "float",
                        "unit": "1/m²",
                        "description": "Normalized quadrupole strength",
                        "readable": True,
                        "writable": True
                    },
                    "current": {
                        "type": "float",
                        "unit": "A",
                        "description": "Magnet current",
                        "readable": True,
                        "writable": False
                    }
                },
                safety_limits={
                    "strength": {"min": -10.0, "max": 10.0, "unit": "1/m"},
                    "k_strength": {"min": -10.0, "max": 10.0, "unit": "1/m²"}
                },
                examples=[
                    "Set Q1M1T1R strength to 2.5",
                    "Get Q2M1T1R k_strength",
                    "List all quadrupoles"
                ]
            ),
            "bpm": DeviceSchema(
                name="bpm",
                type="bpm",
                class_name="BPMDevice",
                description="Beam Position Monitor for measuring beam position",
                attributes={
                    "x_position": {
                        "type": "float",
                        "unit": "mm",
                        "description": "Horizontal beam position",
                        "readable": True,
                        "writable": False
                    },
                    "y_position": {
                        "type": "float",
                        "unit": "mm",
                        "description": "Vertical beam position",
                        "readable": True,
                        "writable": False
                    },
                    "status": {
                        "type": "string",
                        "description": "BPM status",
                        "readable": True,
                        "writable": False
                    }
                },
                examples=[
                    "Get BPM1T1R x position",
                    "Get BPM2T1R y position",
                    "List all BPMs"
                ]
            ),
            "cavity": DeviceSchema(
                name="cavity",
                type="cavity",
                class_name="CavityDevice",
                description="RF cavity for beam acceleration",
                attributes={
                    "frequency": {
                        "type": "float",
                        "unit": "MHz",
                        "description": "Cavity frequency",
                        "readable": True,
                        "writable": True
                    },
                    "phase": {
                        "type": "float",
                        "unit": "deg",
                        "description": "Cavity phase",
                        "readable": True,
                        "writable": True
                    },
                    "voltage": {
                        "type": "float",
                        "unit": "MV",
                        "description": "Cavity voltage",
                        "readable": True,
                        "writable": False
                    }
                },
                safety_limits={
                    "frequency": {"min": 100.0, "max": 500.0, "unit": "MHz"},
                    "voltage": {"min": 0.0, "max": 10.0, "unit": "MV"}
                },
                examples=[
                    "Set CAV1T1R frequency to 352.2 MHz",
                    "Get CAV2T1R phase",
                    "List all cavities"
                ]
            )
        }
        
        # Index by device type
        for device in self.devices.values():
            if device.type not in self.device_types:
                self.device_types[device.type] = []
            self.device_types[device.type].append(device.name)
        
        # Default command templates
        self.commands = {
            "set_power_converter_current": CommandTemplate(
                name="set_power_converter_current",
                description="Set power converter current setpoint",
                natural_language=[
                    "set {device} current to {value}A",
                    "change {device} current to {value} amperes",
                    "set {device} current setpoint to {value}A",
                    "update {device} current to {value} amps"
                ],
                tango_command="dev.current_setpoint = {value}",
                parameters={
                    "device": {"type": "string", "description": "Power converter device name"},
                    "value": {"type": "float", "description": "Current value in amperes"}
                },
                examples=[
                    "set Q3P2T6R current to 5.1A",
                    "change Q1M1T1R current to 10.5 amperes"
                ],
                safety_notes=[
                    "Current must be within 0-1000A range",
                    "Confirm high current changes (>500A)"
                ]
            ),
            "get_power_converter_current": CommandTemplate(
                name="get_power_converter_current",
                description="Get power converter current value",
                natural_language=[
                    "get {device} current",
                    "what is {device} current?",
                    "show {device} current",
                    "read {device} current value"
                ],
                tango_command="dev.current",
                parameters={
                    "device": {"type": "string", "description": "Power converter device name"}
                },
                examples=[
                    "get Q3P2T6R current",
                    "what is Q1M1T1R current?"
                ],
                safety_notes=[]
            ),
            "list_power_converters": CommandTemplate(
                name="list_power_converters",
                description="List all power converter devices",
                natural_language=[
                    "list all power converters",
                    "show power converters",
                    "display power converters",
                    "what power converters are available?"
                ],
                tango_command="get_unique_power_converters()",
                parameters={},
                examples=[
                    "list all power converters",
                    "show power converters"
                ],
                safety_notes=[]
            ),
            "set_quadrupole_strength": CommandTemplate(
                name="set_quadrupole_strength",
                description="Set quadrupole magnet strength",
                natural_language=[
                    "set {device} strength to {value}",
                    "adjust {device} strength to {value}",
                    "change {device} strength to {value}",
                    "set {device} k_strength to {value}"
                ],
                tango_command="dev.strength = {value}",
                parameters={
                    "device": {"type": "string", "description": "Quadrupole device name"},
                    "value": {"type": "float", "description": "Strength value"}
                },
                examples=[
                    "set Q1M1T1R strength to 2.5",
                    "adjust Q2M1T1R k_strength to -1.8"
                ],
                safety_notes=[
                    "Strength must be within -10 to +10 range",
                    "High strength changes may affect beam stability"
                ]
            )
        }
        
        # Default safety rules
        self.safety_rules = {
            "current_limits": {
                "power_converter": {"min": 0.0, "max": 1000.0, "unit": "A"},
                "quadrupole": {"min": 0.0, "max": 100.0, "unit": "A"}
            },
            "voltage_limits": {
                "power_converter": {"min": 0.0, "max": 100.0, "unit": "V"},
                "cavity": {"min": 0.0, "max": 10.0, "unit": "MV"}
            },
            "strength_limits": {
                "quadrupole": {"min": -10.0, "max": 10.0, "unit": "1/m"},
                "sextupole": {"min": -50.0, "max": 50.0, "unit": "1/m²"}
            },
            "confirmation_required": [
                "current > 500A",
                "voltage > 50V",
                "strength > 5.0",
                "frequency change > 10MHz"
            ]
        }
        
        # Default operation modes
        self.operation_modes = {
            "normal": {
                "description": "Normal operation mode",
                "safety_level": "standard",
                "allowed_operations": ["read", "write", "list"]
            },
            "maintenance": {
                "description": "Maintenance mode with relaxed safety",
                "safety_level": "relaxed",
                "allowed_operations": ["read", "write", "list", "calibrate"]
            },
            "emergency": {
                "description": "Emergency mode with strict safety",
                "safety_level": "strict",
                "allowed_operations": ["read", "list"]
            }
        }
    
    def get_device_schema(self, device_name: str) -> Optional[DeviceSchema]:
        """Get device schema by name"""
        return self.devices.get(device_name)
    
    def get_device_schemas_by_type(self, device_type: str) -> List[DeviceSchema]:
        """Get all device schemas of a specific type"""
        device_names = self.device_types.get(device_type, [])
        return [self.devices[name] for name in device_names if name in self.devices]
    
    def get_command_template(self, command_name: str) -> Optional[CommandTemplate]:
        """Get command template by name"""
        return self.commands.get(command_name)
    
    def search_commands(self, query: str) -> List[CommandTemplate]:
        """Search commands by natural language query"""
        results = []
        query_lower = query.lower()
        
        for template in self.commands.values():
            # Search in description and natural language examples
            if (query_lower in template.description.lower() or
                any(query_lower in nl.lower() for nl in template.natural_language)):
                results.append(template)
        
        return results
    
    def get_safety_limits(self, device_type: str, property_name: str) -> Optional[Dict[str, Any]]:
        """Get safety limits for a device property"""
        device_schemas = self.get_device_schemas_by_type(device_type)
        for schema in device_schemas:
            if property_name in schema.safety_limits:
                return schema.safety_limits[property_name]
        return None
    
    def get_operation_mode(self, mode_name: str) -> Optional[Dict[str, Any]]:
        """Get operation mode configuration"""
        return self.operation_modes.get(mode_name)
    
    def validate_operation(self, operation: str, mode: str = "normal") -> bool:
        """Validate if operation is allowed in current mode"""
        mode_config = self.get_operation_mode(mode)
        if not mode_config:
            return False
        
        allowed_operations = mode_config.get("allowed_operations", [])
        return operation in allowed_operations
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of knowledge base"""
        return {
            "total_devices": len(self.devices),
            "device_types": list(self.device_types.keys()),
            "total_commands": len(self.commands),
            "safety_rules": len(self.safety_rules),
            "operation_modes": list(self.operation_modes.keys())
        }
    
    def export_knowledge_base(self, export_path: str):
        """Export knowledge base to files"""
        export_path = Path(export_path)
        export_path.mkdir(parents=True, exist_ok=True)
        
        # Export device schemas
        schemas_path = export_path / "schemas" / "devices"
        schemas_path.mkdir(parents=True, exist_ok=True)
        
        for device_name, schema in self.devices.items():
            schema_file = schemas_path / f"{device_name}.yaml"
            with open(schema_file, 'w') as f:
                yaml.dump(schema.__dict__, f, default_flow_style=False, indent=2)
        
        # Export command templates
        templates_path = export_path / "templates" / "commands"
        templates_path.mkdir(parents=True, exist_ok=True)
        
        for command_name, template in self.commands.items():
            template_file = templates_path / f"{command_name}.yaml"
            with open(template_file, 'w') as f:
                yaml.dump(template.__dict__, f, default_flow_style=False, indent=2)
        
        # Export safety rules
        safety_path = export_path / "safety"
        safety_path.mkdir(parents=True, exist_ok=True)
        
        safety_file = safety_path / "rules.yaml"
        with open(safety_file, 'w') as f:
            yaml.dump(self.safety_rules, f, default_flow_style=False, indent=2)
        
        # Export operation modes
        operations_path = export_path / "operations"
        operations_path.mkdir(parents=True, exist_ok=True)
        
        modes_file = operations_path / "modes.yaml"
        with open(modes_file, 'w') as f:
            yaml.dump(self.operation_modes, f, default_flow_style=False, indent=2)
        
        logger.info(f"Knowledge base exported to {export_path}")
