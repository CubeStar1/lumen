using System.Collections.Generic;
using UnityEngine;

namespace FloorPlanViz.Geometry
{
    /// <summary>Ear-clipping triangulation for simple polygons. Triangles are returned counter-clockwise.</summary>
    public static class PolygonTriangulator
    {
        const float Epsilon = 1e-6f;

        public static List<int> Triangulate(IReadOnlyList<Vector2> polygon)
        {
            var remaining = new List<int>(polygon.Count);
            for (var i = 0; i < polygon.Count; i++)
                remaining.Add(i);
            if (SignedArea(polygon) < 0f)
                remaining.Reverse();

            var triangles = new List<int>();
            while (remaining.Count > 3 && TryClipEar(polygon, remaining, triangles)) { }

            if (remaining.Count == 3)
                triangles.AddRange(remaining);
            return triangles;
        }

        public static float SignedArea(IReadOnlyList<Vector2> polygon)
        {
            var area = 0f;
            for (var i = 0; i < polygon.Count; i++)
            {
                var a = polygon[i];
                var b = polygon[(i + 1) % polygon.Count];
                area += a.x * b.y - b.x * a.y;
            }
            return area / 2f;
        }

        static bool TryClipEar(IReadOnlyList<Vector2> polygon, List<int> remaining, List<int> triangles)
        {
            var count = remaining.Count;
            for (var i = 0; i < count; i++)
            {
                var prev = remaining[(i + count - 1) % count];
                var current = remaining[i];
                var next = remaining[(i + 1) % count];
                var turn = Cross(polygon[current] - polygon[prev], polygon[next] - polygon[current]);

                if (Mathf.Abs(turn) < Epsilon)
                {
                    remaining.RemoveAt(i);
                    return true;
                }
                if (turn > 0f && !ContainsOtherVertex(polygon, remaining, prev, current, next))
                {
                    triangles.AddRange(new[] { prev, current, next });
                    remaining.RemoveAt(i);
                    return true;
                }
            }
            return false;
        }

        static bool ContainsOtherVertex(IReadOnlyList<Vector2> polygon, List<int> remaining, int a, int b, int c)
        {
            foreach (var index in remaining)
            {
                if (index == a || index == b || index == c)
                    continue;
                if (InTriangle(polygon[index], polygon[a], polygon[b], polygon[c]))
                    return true;
            }
            return false;
        }

        static bool InTriangle(Vector2 p, Vector2 a, Vector2 b, Vector2 c) =>
            Cross(b - a, p - a) >= 0f && Cross(c - b, p - b) >= 0f && Cross(a - c, p - c) >= 0f;

        static float Cross(Vector2 a, Vector2 b) => a.x * b.y - a.y * b.x;
    }
}
