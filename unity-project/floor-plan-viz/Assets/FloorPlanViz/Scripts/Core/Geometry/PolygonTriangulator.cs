using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace FloorPlanViz.Geometry
{
    /// <summary>Ear-clipping triangulation for simple polygons, optionally with holes. Triangles are returned counter-clockwise.</summary>
    public static class PolygonTriangulator
    {
        const float Epsilon = 1e-6f;

        /// <summary>Bridges each hole into the outer ring, then triangulates the merged ring. The triangles index into <paramref name="ring"/>.</summary>
        public static List<int> Triangulate(IReadOnlyList<Vector2> outer, IEnumerable<IReadOnlyList<Vector2>> holes, out List<Vector2> ring)
        {
            var oriented = holes.Where(h => h.Count >= 3).Select(h => Oriented(h, counterClockwise: false)).ToList();
            ring = Oriented(outer, counterClockwise: true);
            foreach (var hole in oriented.OrderByDescending(h => h.Max(p => p.x)))
                ring = Bridge(ring, hole, oriented);
            return Triangulate(ring);
        }

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

        public static List<Vector2> Oriented(IReadOnlyList<Vector2> polygon, bool counterClockwise)
        {
            var points = polygon.ToList();
            if (SignedArea(points) > 0f != counterClockwise)
                points.Reverse();
            return points;
        }

        /// <summary>Joins the hole to the ring along a cut from the hole's rightmost vertex to the nearest ring vertex it can see.</summary>
        static List<Vector2> Bridge(List<Vector2> ring, List<Vector2> hole, List<List<Vector2>> holes)
        {
            var start = hole.IndexOf(hole.OrderByDescending(p => p.x).First());
            var from = hole[start];
            var target = Enumerable.Range(0, ring.Count)
                .OrderBy(i => (ring[i] - from).sqrMagnitude)
                .Where(i => Visible(from, ring[i], ring, holes, hole))
                .DefaultIfEmpty(-1)
                .First();
            if (target < 0)
                return ring;

            var merged = ring.Take(target + 1).ToList();
            for (var k = 0; k <= hole.Count; k++)
                merged.Add(hole[(start + k) % hole.Count]);
            merged.Add(ring[target]);
            merged.AddRange(ring.Skip(target + 1));
            return merged;
        }

        static bool Visible(Vector2 a, Vector2 b, List<Vector2> ring, List<List<Vector2>> holes, List<Vector2> own)
        {
            if (Contains(own, (a + b) / 2f))
                return false;
            return !Edges(ring).Concat(holes.SelectMany(Edges)).Any(e => Crosses(a, b, e.Item1, e.Item2));
        }

        static IEnumerable<(Vector2, Vector2)> Edges(List<Vector2> ring) =>
            ring.Select((p, i) => (p, ring[(i + 1) % ring.Count]));

        static bool Crosses(Vector2 a, Vector2 b, Vector2 c, Vector2 d)
        {
            if (Same(a, c) || Same(a, d) || Same(b, c) || Same(b, d))
                return false;
            return Cross(b - a, c - a) * Cross(b - a, d - a) < 0f && Cross(d - c, a - c) * Cross(d - c, b - c) < 0f;
        }

        static bool Contains(List<Vector2> polygon, Vector2 point)
        {
            var inside = false;
            for (int i = 0, j = polygon.Count - 1; i < polygon.Count; j = i++)
            {
                var (p, q) = (polygon[i], polygon[j]);
                if (p.y > point.y != q.y > point.y && point.x < (q.x - p.x) * (point.y - p.y) / (q.y - p.y) + p.x)
                    inside = !inside;
            }
            return inside;
        }

        static bool Same(Vector2 a, Vector2 b) => (a - b).sqrMagnitude < Epsilon;

        static bool ContainsOtherVertex(IReadOnlyList<Vector2> polygon, List<int> remaining, int a, int b, int c)
        {
            foreach (var index in remaining)
            {
                if (index == a || index == b || index == c)
                    continue;
                var p = polygon[index];
                if (Same(p, polygon[a]) || Same(p, polygon[b]) || Same(p, polygon[c]))
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
