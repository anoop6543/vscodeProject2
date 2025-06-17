## Laser Marker Integration

The project now includes a flexible and extensible laser marker integration system, allowing for the simulation of various vendor-specific laser markers in the gantry robot system.

### Laser Marker Architecture

The laser marker system uses a flexible class hierarchy and adapter pattern:

- **Base Class**: `LaserMarker` (abstract)
  - Defines the common interface for all laser marker implementations
  - Handles basic functionality like initialization, status tracking, settings management
  - Declares abstract methods that vendor-specific implementations must provide

- **Vendor-Specific Implementations**:
  - `KeyenceLaserMarker`: Implements Keyence-specific laser marker behavior
  - `TrumpfLaserMarker`: Implements TRUMPF-specific laser marker behavior
  - Additional vendors can be added by implementing new subclasses

- **Adapter**: `LaserMarkerAdapter`
  - Integrates laser markers with the existing `GantryRobot` class
  - Provides a bridge between the robot and laser marker
  - Allows swapping of different laser marker implementations without changing robot code

### Key Features

- **Vendor Flexibility**: Support for different laser marker brands and models
- **Multiple Operation Modes**: Marking, welding, engraving, cutting
- **Model-Specific Settings**: Each laser marker model has appropriate settings and capabilities
- **Dynamic Switching**: Can change laser markers at runtime
- **Consistent Interface**: Common interface for all laser operations, regardless of vendor
- **Visualization Support**: Works with the existing visualization system
- **Laser Parameter Control**: Adjust power, speed, focus, and other parameters

### Supported Laser Types

- **Fiber Lasers**: High-power lasers for marking and welding
- **CO2 Lasers**: Good for marking and cutting non-metallic materials
- **YAG Lasers**: Used for marking and engraving
- **UV Lasers**: Specialized for high-precision marking

### How to Use Laser Markers

#### 1. Basic Usage with Factory Function

```python
from laser_marker import create_laser_marker

# Create a Keyence laser marker
keyence = create_laser_marker("keyence", "MD-F3000")

# Perform marking operation
keyence.mark(
    target_point=(100, 100, 10),
    text="SERIAL-123456",
    power=30,
    speed=100,
    font_size=8.0
)

# Perform welding operation
keyence.weld(
    start_point=(150, 50, 20),
    end_point=(200, 50, 20),
    power=50,
    speed=10,
    focus_setting=0.2
)
```

#### 2. Integration with GantryRobot using Adapter

```python
from SimpleGantrySimulation import GantryRobot
from laser_marker_adapter import LaserMarkerAdapter

# Create a GantryRobot instance
gantry = GantryRobot()

# Create an adapter with a Keyence laser marker
adapter = LaserMarkerAdapter(gantry, vendor="keyence", model="MD-X1500")

# Now the robot can use the laser marker through its laser_weld and laser_mark methods
gantry.laser_weld(
    start_point=(50, 50, 20),
    end_point=(150, 50, 20),
    speed=15,
    power=45,
    focus_setting=0.0
)

gantry.laser_mark(
    target_point=(200, 200, 10),
    text="GANTRY-TEST-123",
    speed=100,
    power=30,
    font_size=5.0
)

# Switch to a different laser marker if needed
adapter.replace_laser_marker("trumpf", "TruMark 6130")
```

#### 3. Integrating with Assembly Scenarios

To add a laser marker to an assembly scenario:

```python
# Import necessary modules
from laser_marker import create_laser_marker
from laser_marker_adapter import LaserMarkerAdapter

# Inside your assembly sequence function
def engine_assembly_sequence():
    # ... existing code ...
    
    # Create a laser marker adapter with a high-power fiber laser for welding
    laser_adapter = LaserMarkerAdapter(gantry, vendor="trumpf", model="TruMark 6130")
    
    # The laser_weld method now uses the TRUMPF laser through the adapter
    gantry.laser_weld(
        start_point=weld_start_point,
        end_point=weld_end_point,
        speed=15,
        power=1800,
        focus_setting=-0.2
    )
    
    # ... continue with the rest of the sequence ...
```

### Vendor-Specific Features

#### Keyence Laser Markers

Keyence laser markers support additional features like:

```python
# Create a job and save it for later use
keyence.save_job("job1", {"text": "TEST-123", "position": (100, 100, 10)})

# Load a previously saved job
keyence.load_job("job1")

# Run the currently loaded job
keyence.run_job()
```

#### TRUMPF Laser Markers

TRUMPF laser markers have their own programming model:

```python
# Create a program and save it
trumpf.save_program("program1", {"text": "TRUMPF-TEST", "position": (120, 120, 15)})

# Load a previously saved program
trumpf.load_program("program1")

# Execute the currently loaded program
trumpf.execute_program()
```

### Testing Laser Markers

A test script is provided to demonstrate the laser marker functionality:

```powershell
python .\tests\test_laser_marker.py
```

This script tests:
- Basic laser marker functionality
- Integration with GantryRobot via the adapter
- Examples of how to modify existing scenarios

### Implementation Details

- **`laser_marker.py`**: Defines the base `LaserMarker` class and vendor-specific implementations
  - Uses abstract base classes to ensure proper implementation
  - Provides a factory function for easy creation of laser markers
  
- **`laser_marker_adapter.py`**: Implements the adapter pattern to integrate laser markers with the GantryRobot
  - Patches the robot's methods to use the laser marker
  - Maintains backward compatibility with existing code

This architecture allows for seamless integration of new laser marker vendors and models, making the system highly extensible while maintaining a consistent interface for the gantry robot operations.
