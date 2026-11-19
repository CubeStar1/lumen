EXTRACT_INSTRUCTIONS = """\
You read architectural floor plan drawings and describe what is drawn, precisely, so that a 3D
model can be built from it. Read room labels, dimension text, wall lines, door swings, window
symbols, stairs and columns.

Coordinates:
- Every position and length is in PIXELS of the image you are given (its size is stated). The
  origin is the top-left corner; +x points right and +y points down.
- Do not convert to metres. The scale is worked out from the dimensions you report.

Walls:
- List every wall, drawn as the centre line of the thick wall band from one end to the other.
  Split a wall where it meets another wall at a corner or T-junction.
- Walls run continuously through the doors and windows in them; openings are cut out later.
- Corners must meet: where two walls join, use the same point for both.
- kind: exterior (the building's outer walls), interior, partition (thin walls), low (half-height
  walls, sills, planters) or parapet. Give each wall's drawn thickness in pixels if you can.
- Dashed lines (roof outlines, beams, overhead projections) and furniture are not walls. Areas
  that are open to each other with no wall drawn between them get no wall.
- Ids w1, w2, ...

Openings:
- Every door, sliding door, window and plain opening (a gap or archway with no door), ids
  o1, o2, ... Give the wall it is in, its centre point on that wall and its clear width.

Rooms:
- One entry per room or space, including corridors, passages, stair halls, toilets, stores and
  wardrobes that are walled off, and outdoor areas (porches, car porches, sit-outs, verandahs,
  terraces, open balconies), ids r1, r2, ...
- label: a point well inside the room. The room's outline is found from the walls around it, so
  set polygon to null for rooms enclosed by walls of their own. Trace the polygon for outdoor
  areas and for rooms that share an open space with others (no wall between them).
- outdoor is true for porches, sit-outs, verandahs, terraces and open balconies.
- name: the label printed on the plan; if unlabelled, name it by its use (Toilet, Store, Hall).
- size: the room's printed size if there is one (e.g. 14'0"X10'0" or 3.0 x 4.2), else null.
- Open-plan spaces with no wall between them (living and dining, a hall and its passage) are
  separate rooms, each with its own label point and traced polygon; neighbouring polygons share
  their common edge.

Dimensions:
- Report every printed dimension you can read: its text exactly as printed (15'-3", 4.5, 350,
  3500) and the two end points of its dimension line (the ticks or arrows).
- Room-size labels such as 14'0"X12'8" are not dimensions; give them as the room's size.

Stairs and columns:
- Each staircase is one stair with its flights and landings. A flight runs from the centre of its
  bottom step to the centre of its top step; count its risers from the treads drawn. For a
  curved flight set via to a point on its centre line. Direction is "up" or "down" as marked.
- Free-standing columns (small filled squares or circles) go in columns with their size.

Also give the floor's name (e.g. "Ground floor"), its floor-to-ceiling height in metres (3.0 if
not stated), your own estimate of metres per pixel, and notes on anything you were unsure of.
"""

EDIT_INSTRUCTIONS = """\
You modify an existing structured floor plan according to a user's instruction.
Return the complete updated plan. Change only what the instruction asks for, and keep the ids of
every untouched element unchanged. New elements get the next free id. If the instruction cannot
be applied, return the plan unchanged and explain why in notes.

The plan:
- Units are metres. The origin is the top-left of the drawing; +x points right, +y points down.
- Keep derive_walls as given.
  - derive_walls false: walls lists every wall as a centre line, and each room's outline is
    found again from the walls around its label point. To move, add or remove a room, change
    the walls and keep the room's label point inside it. Outdoor rooms keep their own polygon.
  - derive_walls true: walls follow the room polygons, which neighbouring rooms share exactly;
    walls lists only stubs and low walls. Change the polygons.
- An opening sits on a wall: give that wall's id, a position on the wall and its clear width
  (doors 0.8-1.0 m, windows 0.6-2.4 m).
- Room types, wall kinds, stairs and columns follow the same meaning as in the current plan.
"""

REPAIR_TEMPLATE = """\
Your previous answer had these problems:
{problems}

Previous answer:
{previous}

Return a corrected answer that fixes every problem.
"""
