using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using UnityEngine;

namespace FloorPlanViz.Geometry
{
    /// <summary>Wall sides and the flat tops of full-height wall pieces, kept apart so the tops can be drawn as a section cut.</summary>
    public readonly struct WallMeshes
    {
        public readonly MeshData Sides;
        public readonly MeshData Caps;

        public WallMeshes(MeshData sides, MeshData caps)
        {
            Sides = sides;
            Caps = caps;
        }
    }

    /// <summary>Builds mesh data for a plan at 1 unit = 1 metre, with plan (x, y) at world (x, 0, y).</summary>
    public static class PlanMeshBuilder
    {
        const float RoofLift = 0.01f;
        const float TopTolerance = 0.001f;
        const float FrameWidth = 0.05f;
        const float GlassThickness = 0.012f;
        const float BaseInset = 0.002f;
        const float RailHeight = 0.9f;
        const float RailSize = 0.05f;
        const float BalusterSize = 0.025f;
        const float BalusterSpacing = 0.15f;

        public static WallMeshes Walls(IEnumerable<WallData> walls)
        {
            var meshes = new WallMeshes(new MeshData(), new MeshData());
            foreach (var wall in walls)
                AddWall(meshes, wall);
            return meshes;
        }

        public static MeshData Floors(IEnumerable<RoomData> rooms)
        {
            var mesh = new MeshData();
            foreach (var room in rooms)
                mesh.AddPolygon(Plan(room.Polygon), room.Holes.Select(Plan).ToList(), 0f, faceUp: true);
            return mesh;
        }

        /// <summary>Solid step blocks and landings.</summary>
        public static MeshData Treads(IEnumerable<StairData> stairs)
        {
            var mesh = new MeshData();
            foreach (var stair in stairs)
            {
                foreach (var step in stair.Steps)
                    mesh.AddPrism(Plan(step.Corners), step.Bottom, step.Top);
                foreach (var landing in stair.Landings)
                    mesh.AddPrism(Plan(landing.Polygon), 0f, landing.Height);
            }
            return mesh;
        }

        /// <summary>Balusters along each railing line with a handrail on top.</summary>
        public static MeshData Railings(IEnumerable<StairData> stairs)
        {
            var mesh = new MeshData();
            foreach (var railing in stairs.SelectMany(s => s.Railings))
            {
                var points = railing.Select(p => p.ToWorld()).ToList();
                for (var i = 0; i + 1 < points.Count; i++)
                {
                    var (a, b) = (points[i], points[i + 1]);
                    var flat = new Vector2(b.x - a.x, b.z - a.z).magnitude;
                    var count = Mathf.Max(1, Mathf.CeilToInt(flat / BalusterSpacing));
                    for (var k = 0; k < count; k++)
                    {
                        var foot = Vector3.Lerp(a, b, k / (float)count);
                        mesh.AddBar(foot, foot + Vector3.up * RailHeight, BalusterSize);
                    }
                    mesh.AddBar(a + Vector3.up * RailHeight, b + Vector3.up * RailHeight, RailSize);
                }
                if (points.Count > 0)
                    mesh.AddBar(points[^1], points[^1] + Vector3.up * RailHeight, BalusterSize);
            }
            return mesh;
        }

        public static MeshData Columns(IEnumerable<ColumnData> columns)
        {
            var mesh = new MeshData();
            foreach (var column in columns)
                mesh.AddBox(column.Position.ToWorld(column.Height / 2f), Quaternion.identity,
                    new Vector3(column.Size, column.Height, column.Size));
            return mesh;
        }

        /// <summary>The underside and edges of each floor slab, including the sides of its stair wells. Its top is the room floors.</summary>
        public static MeshData Slabs(IEnumerable<SlabData> slabs)
        {
            var mesh = new MeshData();
            foreach (var slab in slabs)
            {
                var outline = PolygonTriangulator.Oriented(Plan(slab.Outline), counterClockwise: true);
                var holes = slab.Holes.Select(h => PolygonTriangulator.Oriented(Plan(h), counterClockwise: false)).ToList();
                mesh.AddPolygon(outline, holes.Cast<IReadOnlyList<Vector2>>().ToList(), -slab.Thickness, faceUp: false);
                foreach (var ring in holes.Prepend(outline))
                {
                    for (var i = 0; i < ring.Count; i++)
                        mesh.AddSide(ring[i], ring[(i + 1) % ring.Count], -slab.Thickness, 0f);
                }
            }
            return mesh;
        }

        public static MeshData Roof(IEnumerable<RoomData> rooms, float wallHeight) =>
            Slabs(rooms, wallHeight + RoofLift);

        /// <summary>A board under the whole plan, its top just below the floors.</summary>
        public static MeshData Base(PlanBounds bounds, float margin, float thickness)
        {
            var size = bounds.Size + Vector2.one * (margin * 2f);
            var centre = (bounds.Min.ToVector2() + bounds.Max.ToVector2()) / 2f;
            var mesh = new MeshData();
            mesh.AddBox(new Vector3(centre.x, -BaseInset - thickness / 2f, centre.y), Quaternion.identity,
                new Vector3(size.x, thickness, size.y));
            return mesh;
        }

        public static MeshData Ground(PlanBounds bounds, float margin, float height)
        {
            var min = bounds.Min.ToVector2() - Vector2.one * margin;
            var max = bounds.Max.ToVector2() + Vector2.one * margin;
            var mesh = new MeshData();
            mesh.AddPolygon(new[] { min, new Vector2(max.x, min.y), max, new Vector2(min.x, max.y) }, height, faceUp: true);
            return mesh;
        }

        public static MeshData Glass(IEnumerable<WallData> walls) =>
            Openings(walls, o => o == OpeningType.Window, (mesh, frame) =>
                mesh.AddBox(frame.Centre(frame.Sill, frame.Head), frame.Rotation,
                    new Vector3(GlassThickness, frame.Head - frame.Sill, frame.Width)));

        /// <summary>Window frames with a centre mullion, and door jambs with a head.</summary>
        public static MeshData Frames(IEnumerable<WallData> walls)
        {
            var mesh = Openings(walls, o => o == OpeningType.Window, AddWindowFrame);
            return Openings(walls, o => o.IsDoor(), AddDoorFrame, mesh);
        }

        static MeshData Slabs(IEnumerable<RoomData> rooms, float height)
        {
            var mesh = new MeshData();
            foreach (var room in rooms)
                mesh.AddPolygon(Plan(room.Polygon), height, faceUp: true);
            return mesh;
        }

        static List<Vector2> Plan(IEnumerable<PlanPoint> points) => points.Select(p => p.ToVector2()).ToList();

        static void AddWall(WallMeshes meshes, WallData wall)
        {
            var frame = WallFrame.Of(wall);
            foreach (var piece in WallSlicer.Slice(wall))
            {
                var centre = frame.Along((piece.From + piece.To) / 2f - wall.Thickness / 2f, (piece.Bottom + piece.Top) / 2f);
                var size = new Vector3(wall.Thickness, piece.Height, piece.Length);
                var isTop = piece.Top >= wall.Height - TopTolerance;
                meshes.Sides.AddBox(centre, frame.Rotation, size, includeTop: !isTop);
                if (isTop)
                    meshes.Caps.AddFace(centre + Vector3.up * (piece.Height / 2f), Vector3.up, frame.Rotation * Vector3.forward, size.x, size.z);
            }
        }

        static void AddWindowFrame(MeshData mesh, OpeningFrame frame)
        {
            var depth = frame.Thickness * 0.5f;
            var height = frame.Head - frame.Sill;
            AddFrameBar(mesh, frame, 0f, frame.Sill + FrameWidth / 2f, depth, FrameWidth, frame.Width);
            AddFrameBar(mesh, frame, 0f, frame.Head - FrameWidth / 2f, depth, FrameWidth, frame.Width);
            AddFrameBar(mesh, frame, 0f, (frame.Sill + frame.Head) / 2f, depth, height, FrameWidth * 0.6f);
            foreach (var side in new[] { -1f, 1f })
                AddFrameBar(mesh, frame, side * (frame.Width - FrameWidth) / 2f, (frame.Sill + frame.Head) / 2f, depth, height, FrameWidth);
        }

        static void AddDoorFrame(MeshData mesh, OpeningFrame frame)
        {
            var depth = frame.Thickness + 0.02f;
            AddFrameBar(mesh, frame, 0f, frame.Head + FrameWidth / 2f, depth, FrameWidth, frame.Width + FrameWidth * 2f);
            foreach (var side in new[] { -1f, 1f })
                AddFrameBar(mesh, frame, side * (frame.Width + FrameWidth) / 2f, frame.Head / 2f, depth, frame.Head, FrameWidth);
        }

        static void AddFrameBar(MeshData mesh, OpeningFrame frame, float along, float height, float depth, float barHeight, float barLength) =>
            mesh.AddBox(frame.Centre(height, height, along), frame.Rotation, new Vector3(depth, barHeight, barLength));

        static MeshData Openings(IEnumerable<WallData> walls, System.Func<OpeningType, bool> include, System.Action<MeshData, OpeningFrame> add,
            MeshData mesh = null)
        {
            mesh ??= new MeshData();
            foreach (var wall in walls)
            {
                var frame = WallFrame.Of(wall);
                foreach (var opening in wall.Openings.Where(o => include(o.Type)))
                    add(mesh, new OpeningFrame(frame, opening, wall.Thickness));
            }
            return mesh;
        }

        readonly struct WallFrame
        {
            public readonly Vector2 Start;
            public readonly Vector2 Direction;
            public readonly Quaternion Rotation;

            WallFrame(Vector2 start, Vector2 direction)
            {
                Start = start;
                Direction = direction;
                Rotation = Quaternion.LookRotation(new Vector3(direction.x, 0f, direction.y));
            }

            public static WallFrame Of(WallData wall)
            {
                var start = wall.Start.ToVector2();
                return new WallFrame(start, (wall.End.ToVector2() - start).normalized);
            }

            public Vector3 Along(float distance, float height)
            {
                var point = Start + Direction * distance;
                return new Vector3(point.x, height, point.y);
            }
        }

        readonly struct OpeningFrame
        {
            readonly WallFrame wall;
            readonly float offset;
            public readonly float Width;
            public readonly float Sill;
            public readonly float Head;
            public readonly float Thickness;

            public OpeningFrame(WallFrame wall, OpeningData opening, float thickness)
            {
                this.wall = wall;
                offset = opening.Offset;
                Width = opening.Width;
                Sill = opening.Sill;
                Head = opening.Head;
                Thickness = thickness;
            }

            public Quaternion Rotation => wall.Rotation;

            public Vector3 Centre(float bottom, float top, float along = 0f) =>
                wall.Along(offset + along, (bottom + top) / 2f);
        }
    }
}
