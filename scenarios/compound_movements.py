def arc_move(self, start_point, end_point, center_point, speed):
    """
    Move in an arc from start to end around center point
    Useful for avoiding obstacles or natural curved paths
    """
    """
    import math

    # Extract coordinates
    x1, y1, z1 = start_point
    x2, y2, _ = end_point  # z2 is not used, Z is constant
    xc, yc = center_point

    # Calculate radii from center to start and end points
    r1 = math.sqrt((x1 - xc)**2 + (y1 - yc)**2)
    r2 = math.sqrt((x2 - xc)**2 + (y2 - yc)**2)

    # Check if radii are close enough to be considered equal
    if not math.isclose(r1, r2, rel_tol=1e-5):
        print(f"Warning: Start and end points are not equidistant from the center. r1={r1}, r2={r2}")
        # For simplicity, we'll use the radius of the start_point
        # Alternatively, could raise an error or average them.
    
    radius = r1

    if radius == 0:
        print("Error: Radius is zero. Cannot form an arc.")
        return

    # Calculate start and end angles
    start_angle = math.atan2(y1 - yc, x1 - xc)
    end_angle = math.atan2(y2 - yc, x2 - xc)

    # Determine the direction of the arc (shortest path)
    # Normalize angles to be between 0 and 2*pi
    start_angle_norm = start_angle % (2 * math.pi)
    end_angle_norm = end_angle % (2 * math.pi)

    angle_diff = end_angle_norm - start_angle_norm

    # If the difference is more than pi, go the other way
    if angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    elif angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    
    # Define a reasonable step size for the angle (e.g., 0.1 radians)
    # Smaller step_angle means more points and smoother arc
    # Angular speed can be derived from linear speed: omega = v / r
    if radius == 0: # Should be caught by earlier check, but for safety
        angular_speed = 0.1 # default small step if radius is zero (should not happen)
    else:
        angular_speed = speed / radius
    
    # step_angle should be small enough for smooth movement
    # Let's target roughly 50 steps for a full circle, adjust based on angular_speed
    # A fixed small angle like 0.05 rad is also an option.
    # Max angle diff is 2*pi.
    # Number of steps:
    if abs(angle_diff) < 1e-6: # Start and end are effectively the same point
        num_steps = 1
    else:
        # Estimate time: T = angle_diff / angular_speed
        # Number of steps can be T * some_frequency, or based on fixed angle increment
        # Let's use a fixed angular increment for simplicity here.
        # A smaller angle_increment leads to more points.
        angle_increment_fixed = 0.05 # radians, about 3 degrees
        num_steps = max(2, int(abs(angle_diff) / angle_increment_fixed))


    print(f"Arc Move: Start: {start_point}, End: {end_point}, Center: {center_point}")
    print(f"Radius: {radius:.2f}, Start Angle: {math.degrees(start_angle):.2f} deg, End Angle: {math.degrees(end_angle):.2f} deg")
    print(f"Angle difference: {math.degrees(angle_diff):.2f} deg, Number of steps: {num_steps}")

    if num_steps <= 1 and not math.isclose(start_angle, end_angle, abs_tol=1e-3): # Check if start and end are not the same
         # If start and end points are the same, just print start and end
        if math.isclose(x1, x2) and math.isclose(y1, y2):
            print(f"Step 0: ({x1:.2f}, {y1:.2f}, {z1:.2f})")
            print(f"Step 1: ({x2:.2f}, {y2:.2f}, {z1:.2f})") # z from start_point
            return
        # If num_steps is too small for a significant arc, recalculate
        # This can happen if angle_diff is very small but non-zero
        print(f"Warning: num_steps is {num_steps}, potentially too small for distinct start/end. Recalculating num_steps.")
        # Ensure at least a few steps if there is a noticeable angle difference
        num_steps = max(2, int(abs(angle_diff) / 0.01)) # Use smaller increment for small arcs
        print(f"Recalculated num_steps: {num_steps}")


    for i in range(num_steps + 1):
        # Interpolate angle
        current_angle = start_angle + (angle_diff / num_steps) * i
        
        # Calculate intermediate point coordinates
        x = xc + radius * math.cos(current_angle)
        y = yc + radius * math.sin(current_angle)
        z = z1  # Keep Z constant from start_point

        print(f"Step {i}: ({x:.2f}, {y:.2f}, {z:.2f}) at angle {math.degrees(current_angle):.2f} deg")

    # Ensure the final point is exactly the end_point (or very close)
    # This helps correct for potential floating point inaccuracies over many steps
    # However, given the calculation, the last point should naturally be the end_point
    # if end_angle was used directly. Here, we are interpolating.
    # Let's print the intended end_point based on calculation to compare
    final_calc_x = xc + radius * math.cos(start_angle + angle_diff)
    final_calc_y = yc + radius * math.sin(start_angle + angle_diff)
    # print(f"Calculated final point: ({final_calc_x:.2f}, {final_calc_y:.2f}, {z1:.2f})")
    # print(f"Target end point:       ({x2:.2f}, {y2:.2f}, {z1:.2f})")

    # It's better practice for the simulation part to ensure it reaches end_point
    # For this function, printing the calculated path is the main goal.

def spiral_move(self, center, start_radius, end_radius, angle_increment, z_increment):
    """
    Move in a spiral pattern - useful for adhesive application or scanning
    """
    """
    import math

    xc, yc = center
    
    # Define how much radius changes per full 2*pi rotation.
    # This could be a parameter if more flexibility is needed.
    radius_change_per_rotation = 10.0  # e.g., 10 mm per rotation
    
    if math.isclose(start_radius, end_radius):
        total_rotations = 1.0 # Default to 1 rotation if start and end radius are the same (e.g. cylindrical path)
        if math.isclose(radius_change_per_rotation, 0): # Avoid division by zero if no change per rotation specified
             print("Error: start_radius and end_radius are the same, but radius_change_per_rotation is zero.")
             return
    elif math.isclose(radius_change_per_rotation, 0):
        print("Error: radius_change_per_rotation is zero, cannot determine total rotations for changing radius.")
        return
    else:
        total_rotations = abs(end_radius - start_radius) / radius_change_per_rotation

    total_angle = total_rotations * 2 * math.pi
    
    # Determine direction of radius change
    if math.isclose(start_radius, end_radius):
        radius_change_per_step = 0
    elif end_radius > start_radius:
        radius_change_direction = 1
    else: # end_radius < start_radius
        radius_change_direction = -1

    if math.isclose(angle_increment,0):
        print("Error: angle_increment cannot be zero.")
        return
        
    num_steps = int(abs(total_angle) / abs(angle_increment))
    if num_steps == 0:
        print("Warning: num_steps is zero. Check total_angle and angle_increment.")
        # Print just the start point if no steps
        print(f"Step 0 (start): ({xc + start_radius * math.cos(0):.2f}, {yc + start_radius * math.sin(0):.2f}, {0.0:.2f})")
        if not (math.isclose(start_radius, end_radius) and math.isclose(z_increment*num_steps, 0)):
             # If it's not a stationary point, print end point
            final_x = xc + end_radius * math.cos(total_angle)
            final_y = yc + end_radius * math.sin(total_angle)
            final_z = num_steps * z_increment # This would be 0 if num_steps is 0.
            print(f"Step 0 (end): ({final_x:.2f}, {final_y:.2f}, {final_z:.2f})")
        return

    # Recalculate radius_change_per_step based on num_steps to ensure end_radius is met
    if not math.isclose(start_radius, end_radius):
         actual_radius_change_per_step = (end_radius - start_radius) / num_steps
    else:
         actual_radius_change_per_step = 0

    current_radius = start_radius
    current_angle = 0
    current_z = 0.0  # Relative Z movement, starts at 0 for this function

    print(f"Spiral Move: Center: {center}, Start Radius: {start_radius}, End Radius: {end_radius}")
    print(f"Total Rotations: {total_rotations:.2f}, Total Angle: {math.degrees(total_angle):.2f} deg")
    print(f"Angle Increment: {math.degrees(angle_increment):.2f} deg/step, Z Increment: {z_increment}/step")
    print(f"Number of Steps: {num_steps}, Calculated Radius Change Per Step: {actual_radius_change_per_step:.4f}")

    for i in range(num_steps + 1):
        x = xc + current_radius * math.cos(current_angle)
        y = yc + current_radius * math.sin(current_angle)
        z = current_z
        
        print(f"Step {i}: Pt=({x:.2f}, {y:.2f}, {z:.2f}), R={current_radius:.2f}, A={math.degrees(current_angle % (2*math.pi)):.2f} deg")

        if i < num_steps: # Avoid incrementing beyond the last step
            current_angle += angle_increment
            current_radius += actual_radius_change_per_step
            current_z += z_increment
    
    # Print the final intended point to verify
    # final_x_calc = xc + end_radius * math.cos(total_angle)
    # final_y_calc = yc + end_radius * math.sin(total_angle)
    # final_z_calc = num_steps * z_increment
    # print(f"Final Calculated Point: ({final_x_calc:.2f}, {final_y_calc:.2f}, {final_z_calc:.2f})")