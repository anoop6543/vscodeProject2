def process_serial_data(serial_data):
    """
    Processes a large string read from a serial device.
    Extracts 16 comma-separated values, converts them to floats,
    and ensures the data stream starts with $l and ends with $r.

    Args:
        serial_data (str): The raw data string from the serial device.

    Returns:
        tuple: (success, result) where:
            - success (bool): True if processing was successful, False otherwise
            - result: List of 16 float values if successful, error message if not
    """
    # Handle empty or None input
    if not serial_data:
        return False, "Empty or None input data"
    
    # Trim whitespace
    serial_data = serial_data.strip()
    
    # Check if the data starts with $l
    if not serial_data.startswith("$l"):
        return False, "Invalid data format: Missing start marker $l"
    
    # Check if the data ends with $r
    if not serial_data.endswith("$r"):
        return False, "Invalid data format: Missing end marker $r"

    # Remove the start and end markers
    trimmed_data = serial_data[2:-2].strip()

    # Split the data by commas
    values = [v.strip() for v in trimmed_data.split(',')]

    # Ensure there are exactly 16 values
    if len(values) != 16:
        return False, f"Invalid data format: Expected 16 values, got {len(values)}"

    try:
        # Convert the values to floats
        float_values = [float(value) for value in values]
    except ValueError as e:
        return False, f"Error converting values to floats: {e}"

    return True, float_values


# Example usage
if __name__ == "__main__":
    # Various test cases
    test_cases = [
        "$l1.23,4.56,7.89,0.12,3.45,6.78,9.01,2.34,5.67,8.90,1.11,2.22,3.33,4.44,5.55,6.66$r",  # Valid
        "1.23,4.56,7.89,0.12,3.45,6.78,9.01,2.34,5.67,8.90,1.11,2.22,3.33,4.44,5.55,6.66$r",    # Missing start
        "$l1.23,4.56,7.89,0.12,3.45,6.78,9.01,2.34,5.67,8.90,1.11,2.22,3.33,4.44,5.55",         # Missing end and one value
        "$l1.23,4.56,7.89,0.12,3.45,6.78,9.01,2.34,5.67,8.90,1.11,2.22,3.33,4.44,5.55,ERROR$r"  # Non-float value
    ]

    for i, raw_data in enumerate(test_cases):
        print(f"\nTest case {i+1}: {raw_data}")
        success, result = process_serial_data(raw_data)
        
        if success:
            print("Success! Processed values:", result)
        else:
            print("Failed:", result)

# Example usage with actual serial data
if __name__ == "__main__":
    import serial
    
    # Replace with your serial port and baud rate
    ser = serial.Serial('COM3', 9600, timeout=1)
    
    try:
        # Read data from the serial port
        raw_data = ser.readline().decode('utf-8')
        print(f"Raw data received: {raw_data}")
        
        # Process the data
        success, result = process_serial_data(raw_data)
        
        if success:
            print("Success! Processed values:", result)
        else:
            print("Failed:", result)
    finally:
        ser.close()