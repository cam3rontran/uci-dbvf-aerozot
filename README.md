# uci-dbvf-aerozot
UCI's Official AeroZot Avionics Software



**Note: Please update the README with descriptions of the changes made to the repository and the status for each subtask**



**Computer Vision** (Ownership: @Thea Tan & @Shravan Ramakrishna)

Status: 
  - In testing phase

Notes:

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

**Control** (Ownership: @Richard Nguyen)

Status:

Notes:

  Notes: 
  - Safety handling was already addressed with _check_flight, but fixed possible edge case with "stop" method
  - Added stop decision, might add confidence parameter 

