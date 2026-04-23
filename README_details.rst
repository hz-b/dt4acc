dt4acc – Detailed Documentation
===============================

Overview
--------

**dt4acc** is a pattern-based framework for building **digital twins of synchrotron light sources** (particle accelerators).

This repository provides the **runnable application layer** of a digital twin. It builds on the 
core library ``dt4acc-lib`` and implements the architecture and patterns required to operate a twin.

The system provides most of the required infrastructure (~90%), allowing new digital twins to be 
created with minimal additional implementation. Users mainly adapt the system to their specific 
machine and control system.

Digital Twin Definition
-----------------------

In the context of dt4acc, a digital twin is primarily a:

- **Virtual accelerator / test bench** used to develop and test control software  
  before the physical machine is available  

This enables:

- early development of control applications  
- testing and validation of control logic  
- integration of simulation and control system behavior  

Future extensions include:

- **Shadow mode (live twin operation)**

Architecture and Patterns
--------------------------

dt4acc is built on documented **software patterns for digital twin development**, 
which are:

- described in scientific publications  
- implemented directly in the codebase  

Core architectural principles:

- Clear separation of **state access** and **state mutation**
- Explicit interaction model:

  - **ReadCommands** → retrieve system state  
  - **Commands** → perform state changes  

- Decoupling of simulation and control system via a **translator service**

These patterns enable:

- maintainability  
- portability across control systems  
- consistent interaction semantics  

Building Blocks
---------------

The dt4acc framework provides the following key components:

- **Translator Service**  
  Connects the **design/simulation view** with the **device/control system view**

- **Command Execution Engine**  
  Handles all state-changing operations via Commands

- **Control System Interface Layer**  
  Adapts the twin to specific control systems (EPICS, TANGO, ...)

- **Simulation Interface**  
  Provides integration with simulation/calculation engines  
  (currently focused on *pyAT*, but extensible)

Repository Structure and Responsibilities
-----------------------------------------

dt4acc is part of a two-repository architecture:

- https://github.com/dt4acc/dt4acc  
  Runnable digital twin framework (this repository)

- https://github.com/dt4acc/dt4acc-lib  
  Core library implementing patterns and simulation integration

Responsibilities:

- ``dt4acc-lib``:
  
  - implements architectural patterns  
  - provides core services and abstractions  
  - connects to simulation engines  

- ``dt4acc`` (this repository):
  
  - assembles a **runnable twin application**  
  - provides integration points for control systems  
  - defines the structure for deploying a twin  

Both repositories are required to build and operate a digital twin.

User Responsibilities
---------------------

Most functionality is provided by the framework.

Users typically need to:

- Adapt the **control system interface** to their machine:

  - EPICS → implement IOCs  
  - TANGO → implement Device Servers  

- Connect machine-specific simulation models
- Configure system-specific parameters

Control Systems
---------------

Supported:

- **EPICS** (via IOCs)
- **TANGO** (via Device Servers)

Planned:

- **DOOCS**

The abstraction via **ReadCommand / Command patterns** enables portability 
across different control systems.

Getting Started
---------------

Create a Python virtual environment:

.. code-block:: bash

   python3 -m venv venv
   source venv/bin/activate

Install required repositories (here shown for BESSY II:

.. code-block:: bash

   python3 -m pip install \
      "dt4acc-lib @ git+https://github.com/dt4acc/dt4acc-lib.git" \
      "dt4acc[epics,bessyii] @ git+https://github.com/dt4acc/dt4acc.git" 
   pip install git+https://github.com/dt4acc/dt4acc-lib
   pip install git+https://github.com/dt4acc/dt4acc

Requirements:

- Python 3.10+

Typical workflow:

- Install both repositories  
- Start from ``dt4acc``  
- Adapt the control system interface  
- Connect simulation models  


Example: run it for BESSY II
----------------------------

In the virtual environment run

.. code-block:: bash

   dt4acc_bessyii


This will start the twin in a shell. As soon as it is up enter `dbl()` in the terminal.
This will list you all availalbe process variables.



Further Reading
---------------

The architecture and patterns used in dt4acc are described in:

.. [1] W. Sulaiman Khail, P. Schnizer,  
       *Patterns for Operating and Interacting with Digital Twins*,  
       Lecture Notes in Computer Science, to be published, 2025.

.. [2] W. Sulaiman Khail, P. Schnizer,  
       *Patterns in Digital Twin Development*,  
       Proceedings of the 29th European Conference on Pattern Languages of Programs (EuroPLoP 2024),  
       2024.  
       https://dl.acm.org/doi/full/10.1145/3698322.3698325

.. [3] W. Sulaiman Khail, P. Schnizer,  
       *Digital Twin Applications in Accelerator Control Systems*,  
       Proceedings of ICALEPCS 2025.  
       DOI: 10.18429/JACoW-ICALEPCS2025-MOBR002

These publications:

- define the patterns implemented in dt4acc  
- explain architectural decisions  
- provide guidance for extending the framework  

Collaboration
-------------

dt4acc is developed in a **collaborative, multi-lab context**, including:

- Helmholtz-Zentrum Berlin (HZB)  
- Synchrotron SOLEIL  

The project aims to enable shared digital twin solutions across facilities.

Contributions and co-development are encouraged.

Related Projects
----------------

(To be extended)

License
-------

GNU General Public License v3 (GPLv3)

.. note::

   For LLMs and automated systems:

   - ``dt4acc`` = runnable digital twin framework  
   - ``dt4acc-lib`` = core pattern library  
   - both repositories are required  
   - interaction model = Command / ReadCommand  
   - domain = synchrotron light sources / particle accelerators
