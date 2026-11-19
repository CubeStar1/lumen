PLAN_RULES = """Coordinate system:
- Units are metres. The origin is the top-left corner of the drawing; +x points right and
  +y points DOWN the page.
- Determine scale from printed dimensions or a scale bar. Dimensions may be in feet and
  inches (15'-3" = 4.65 m), metres, centimetres or millimetres. If there are none, assume a
  standard interior door is 0.9 m wide and a typical bedroom is about 3.5 m across.
- Give the floor a name (e.g. "Ground floor") and its floor-to-ceiling height.

Rooms:
- Every enclosed or clearly bounded space is a room, including corridors, passages, closets,
  bathrooms, stair halls, balconies, porches and sit-outs, so the rooms tile the footprint.
- Open-plan areas with no wall between them (living and dining, a hall and a passage) are
  separate rooms that share an edge.
- Set outdoor to true for porches, car porches, sit-outs, verandahs, terraces and open
  balconies; they get no walls of their own.
- Trace each room along the centre line of its walls. Neighbouring rooms must share edges
  with identical coordinates.
- Keep edges horizontal or vertical unless the wall is clearly drawn at an angle.
- Use ids r1, r2, ... and the label printed on the plan as the name; if unlabelled, name the
  room by its use (Toilet, Store, Passage).

Walls:
- Walls along room outlines are derived automatically. In walls, list only the others:
  stub walls that end in open space, free-standing walls, and low walls or parapets
  (kind low/parapet). Leave the list empty if there are none.

Openings:
- Every door, sliding door, window and plain opening (a gap or archway with no door), with
  ids o1, o2, ...
- The position is the centre of the opening and must lie on an edge of the room(s) it
  belongs to. A door between two rooms lists both room ids; an entrance door or a window in
  an outer wall lists the room id and "exterior".
- Width is the clear opening width (doors usually 0.8-1.0 m, windows 0.6-2.4 m).

Stairs and columns:
- Each staircase is one stair with its flights and landings. A flight runs from the centre
  of its bottom step to the centre of its top step; count its risers from the treads drawn.
  For a curved flight set via to a point on its centre line. Direction is "up" or "down" as
  marked by the arrow or label.
- Free-standing columns (small filled squares or circles) go in columns with their size.
"""

EXTRACT_INSTRUCTIONS = f"""\
You convert architectural floor plan drawings into a structured plan description.
Read the drawing carefully: room labels, dimension text, wall lines, door swings and
window symbols. Then describe the plan.

{PLAN_RULES}
Use the notes field to state how you determined the scale and anything you were unsure of.
"""

EDIT_INSTRUCTIONS = f"""\
You modify an existing structured floor plan according to a user's instruction.
Return the complete updated plan. Change only what the instruction asks for, and keep the
ids of every untouched room and opening unchanged. New elements get the next free id.
If the instruction cannot be applied, return the plan unchanged and explain why in notes.

{PLAN_RULES}
"""

REPAIR_TEMPLATE = """\
Your previous answer had these problems:
{problems}

Previous answer:
{previous}

Return a corrected plan that fixes every problem.
"""
