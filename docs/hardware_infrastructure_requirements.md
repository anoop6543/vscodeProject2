# Hardware and Infrastructure Requirements

This document details the necessary hardware, infrastructure, and computing resources required to deploy the Gantry Robot System in a real-world environment, based on the current simulation specifications.

## 1. Robotic Hardware

### 1.1 Gantry System
*   **Frame Structure**: 3-Axis Cartesian Gantry (X, Y, Z) capable of covering the required workspace (approx. 2000mm x 2000mm x 1500mm based on simulation limits).
*   **Linear Actuators**:
    *   **X-Axis**: High-speed belt or ball screw drive (Travel: ~2000mm).
    *   **Y-Axis**: High-speed belt or ball screw drive (Travel: ~2000mm).
    *   **Z-Axis**: Ball screw or rack & pinion vertical drive (Travel: ~1500mm), with brake for safety.
*   **Motors**: 8x Servo Motors with Encoders.
    *   Axis X, Y, Z (Main Gantry)
    *   Extend/Retract (Telescopic arm if applicable)
    *   Rotate (End effector rotation)
    *   Tilt (End effector tilt)
    *   Gripper actuation
*   **Drives**: 8x Servo Drives compatible with the chosen motors and control bus (e.g., EtherCAT, Profinet).

### 1.2 End Effectors (Interchangeable)
The system supports multiple gripper types and tools. A tool changer mechanism is recommended.
*   **Suction Gripper**: Vacuum generator (venturi or pump), suction cups, vacuum sensor.
*   **Parallel Gripper**: Pneumatic or electric 2-finger gripper.
*   **Magnetic Gripper**: Electromagnet or permanent magnet with release mechanism.
*   **Soft Gripper**: Pneumatic soft fingers for fragile objects.
*   **Laser Marker Head**:
    *   **Supported Models**: Keyence MD-X1500/MD-F3000, TRUMPF TruMark 5010/6130, Coherent PowerLine.
    *   **Mounting**: Custom bracket for gantry Z-axis.
    *   **Safety**: Laser safety shutter and fume extractor nozzle.

### 1.3 Sensors
*   **Position Sensors**: Absolute encoders on all motor axes.
*   **Force/Torque Sensor**: 6-axis force/torque sensor mounted at the wrist for feedback.
*   **Proximity Sensors**: Inductive/capacitive sensors for homing and limit detection.
*   **Vision System (Optional)**: Camera for object detection (implied by "Scan" operations).

## 2. Control System

### 2.1 Motion Controller / PLC
*   **Main Controller**: Industrial PC (IPC) or High-performance PLC (e.g., Siemens S7-1500, Beckhoff CX).
    *   Must support real-time motion control for 8 axes.
    *   Interface: OPC UA Server capability for integration with the simulation/SCADA layer.
*   **I/O Modules**:
    *   Digital Inputs: Sensors, buttons, switches.
    *   Digital Outputs: Relays, lights, valves.
    *   Analog I/O: Pressure sensors, analog control signals.

### 2.2 ROS2 Computing Infrastructure
*   **ROS2 Host**: Dedicated Industrial PC or Edge Gateway (e.g., NVIDIA Jetson AGX Orin or x86 IPC).
    *   **OS**: Ubuntu Linux 22.04 LTS (recommended for ROS2 Humble/Iron).
    *   **Software**: ROS2 (Humble/Iron), `ros2_control` stack, custom bridge nodes.
    *   **Network**: Gigabit Ethernet connection to the Main Controller/PLC.

## 3. Infrastructure & Utilities

### 3.1 Power Supply
*   **Main Power**: 3-Phase AC (voltage depends on region/motors, e.g., 400V/480V) for servo drives.
*   **Control Power**: Single-phase AC (110V/230V) and 24V DC power supplies for logic, sensors, and I/O.
*   **UPS**: Uninterruptible Power Supply for the control PC and critical safety logic.

### 3.2 Pneumatics
*   **Air Supply**: Clean, dry compressed air (approx. 6-8 bar) for pneumatic grippers and tool changers.
*   **Preparation Unit**: Filter, Regulator, Lubricator (FRL).
*   **Valves**: Solenoid valve manifold for controlling air flow to grippers.

### 3.3 Network
*   **Industrial Ethernet**: Switch for connecting PLC, Drives, HMI, and ROS2 Host (e.g., EtherCAT, Profinet, or standard TCP/IP for OPC UA).
*   **Remote Access**: VPN router for remote maintenance (optional).

### 3.4 Safety System
*   **Safety PLC/Controller**: Integrated or separate safety controller.
*   **E-Stops**: Emergency stop buttons at operator stations and on the teach pendant.
*   **Perimeter Guarding**: Safety fencing with interlocked doors.
*   **Light Curtains**: For open access points (e.g., loading/unloading zones).
*   **Laser Safety**:
    *   Class 1 Laser Safety Enclosure (if laser marking is automated).
    *   Interlocks connected to the laser controller to prevent firing if the enclosure is open.
    *   "Laser On" warning lights.

## 4. Workcell Environment
*   **Mounting Surface**: Heavy-duty optical table or leveled industrial floor.
*   **Fume Extraction**: Industrial fume extractor for laser marking applications.
*   **Lighting**: Adequate task lighting for vision systems and operator maintenance.
*   **Containment Unit**: For hazardous material scenarios (lead-lined or specific material handling zones).

## 5. Software Stack
*   **Simulation/Digital Twin**: The Python-based simulation provided in this project.
*   **HMI/SCADA**: Web-based dashboard (implied by `ui_interaction_service`) or dedicated HMI panel.
*   **Database**: SQL or NoSQL database for logging recipes, results, and KPIs (simulated by `sim_database_manager`).
