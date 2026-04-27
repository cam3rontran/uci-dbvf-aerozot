# uci-dbvf-aerozot
UCI's Official AeroZot Avionics Software



**Note: Please update the README with descriptions of the changes made to the repository and the status for each subtask**



**Computer Vision** (Ownership: @Thea Tan & @Shravan Ramakrishna)

Status: 
  - fixed detection return format and added frame validation
  - can output structured detection in json file
  - created lidar.py


Notes:
  - (addressed) Convert dummy bounding box into consistent detection data
    - {detected: True/False, x: int, y: int}
  - (addressed) Add basic validation:
    - If no frame, return {detected: False}
  - You may start implementing lidar.py, use placeholder values
  - Optional: Begin simple filtering/smoothing of detection (reduce jitter)

**Mission** (Ownership: @Samyak Anand)

Status:
  - Added the instruction parsing so I can now take Vision module's output
    and feed it into Mission module
  - Added basic test instruction execution so module now executes based 
    on the label that is detected from the most recently obtained frame 
    from Vision

Notes:
  - Debug is NOT ready yet, I still need to write the file parser to execute
    the next Vision output properly
  - The module may be over encompassing right now, if needed I can adjust it to
    simply output to the Control module

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
  - You may start implementing `actions.py`:
    - Purpose: translate mission decisions → control function calls
    - `droneinterface.py` defines how the drone moves
  - Optional: Add STOP or hover behavior

