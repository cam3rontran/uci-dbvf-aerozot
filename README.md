# uci-dbvf-aerozot
UCI's Official AeroZot Avionics Software



**Note: Please update the README with descirptions of the changes made to the repository and the status for each subtask**



**Computer Vision** (Ownership- @Thea Tan & @Shravan Ramakrishna)

Status: 


Notes:
  - Convert dummy bounding box into consistent detection data
    - {detected: True/False, x: int, y: int}
  - Add basic validation:
    - If no frame, return {detected: False}
  - Optional: Begin simple filtering/smoothing of detection (reduce jitter)

**Mission** (Ownership: @Samyak Anand)

Status:


Notes:
  - Implement the "decider" function
  - Must return one of the following:
    - "MOVE_FORWARD"
    - "MOVE_LEFT"
    - "MOVE_RIGHT"
    - "SEARCH"
  - Use detection input:
    - If no detection, "SEARCH"
    - Use x-position for directional movement

**Control** (Ownership: @Richard Nguyen)

Status:


Notes:
  - Required fixes:
    - Add missing firmware functions:
      - takeoff(), disarm(), apply_movement(), emergency_land()
    - Fix import case sensitivity (firmware vs Firmware)
  - Finalize execute_action() function
  - Add safety handling:
    - Prevent movement if not armed/airborne
  - Optional: Add STOP or hover behavior

