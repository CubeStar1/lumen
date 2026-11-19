using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using FloorPlanViz.Geometry;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Draws a top-down 2D view of one level: room fills, walls and openings.</summary>
    [RequireComponent(typeof(CanvasRenderer))]
    public sealed class PlanOutlineGraphic : MaskableGraphic
    {
        const float Margin = 0.9f;
        const float MinWallPixels = 2.5f;
        const float WindowLine = 0.35f;
        const float OutdoorAlpha = 0.45f;

        static readonly Color WallColour = Theme.Hex(0x2C2C2E);
        static readonly Color WindowColour = Theme.Hex(0x64A8FF);

        LevelGeometry level;
        PlanBounds bounds;

        public void SetGeometry(LevelGeometry value, PlanBounds frame)
        {
            level = value;
            bounds = frame;
            SetVerticesDirty();
        }

        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();
            if (level == null || level.Rooms.Count == 0)
                return;

            var rect = rectTransform.rect;
            var size = bounds.Size;
            var scale = Mathf.Min(rect.width / size.x, rect.height / size.y) * Margin;
            var centre = (bounds.Min.ToVector2() + bounds.Max.ToVector2()) / 2f;
            Vector2 ToRect(Vector2 p) => rect.center + (p - centre) * scale;

            foreach (var room in level.Rooms)
            {
                var colour = RoomStyle.Colour(room.Type);
                if (room.Outdoor)
                    colour.a *= OutdoorAlpha;
                AddPolygon(vh, room.Polygon.Select(p => ToRect(p.ToVector2())).ToList(), colour);
            }

            foreach (var wall in level.Walls)
            {
                var start = wall.Start.ToVector2();
                var direction = (wall.End.ToVector2() - start).normalized;
                var thickness = Mathf.Max(wall.Thickness * scale, MinWallPixels);
                AddSegment(vh, ToRect(start), ToRect(wall.End.ToVector2()), thickness, WallColour);

                foreach (var opening in wall.Openings)
                {
                    var from = ToRect(start + direction * (opening.Offset - opening.Width / 2f));
                    var to = ToRect(start + direction * (opening.Offset + opening.Width / 2f));
                    if (opening.Type != OpeningType.Window)
                        AddSegment(vh, from, to, thickness * 1.1f, Theme.Surface, extend: false);
                    else
                    {
                        AddSegment(vh, from, to, thickness * 1.02f, Theme.Surface, extend: false);
                        AddSegment(vh, from, to, thickness * WindowLine, WindowColour, extend: false);
                    }
                }
            }
        }

        static void AddPolygon(VertexHelper vh, List<Vector2> points, Color colour)
        {
            var start = vh.currentVertCount;
            foreach (var point in points)
                vh.AddVert(point, colour, Vector4.zero);

            var triangles = PolygonTriangulator.Triangulate(points);
            for (var i = 0; i < triangles.Count; i += 3)
                vh.AddTriangle(start + triangles[i], start + triangles[i + 1], start + triangles[i + 2]);
        }

        static void AddSegment(VertexHelper vh, Vector2 from, Vector2 to, float thickness, Color colour, bool extend = true)
        {
            var along = (to - from).normalized;
            var side = new Vector2(-along.y, along.x) * (thickness / 2f);
            if (extend)
            {
                from -= along * (thickness / 2f);
                to += along * (thickness / 2f);
            }

            var start = vh.currentVertCount;
            vh.AddVert(from - side, colour, Vector4.zero);
            vh.AddVert(from + side, colour, Vector4.zero);
            vh.AddVert(to + side, colour, Vector4.zero);
            vh.AddVert(to - side, colour, Vector4.zero);
            vh.AddTriangle(start, start + 1, start + 2);
            vh.AddTriangle(start, start + 2, start + 3);
        }
    }
}
