using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Api;
using FloorPlanViz.Data;
using FloorPlanViz.Geometry;
using NUnit.Framework;
using UnityEngine;

namespace FloorPlanViz.Tests
{
    public sealed class StairMeshTests
    {
        const string LevelJson = @"{
            ""index"": 1, ""name"": ""First floor"", ""elevation"": 3.15, ""height"": 3.0,
            ""rooms"": [], ""walls"": [],
            ""stairs"": [{
                ""id"": ""s1"", ""direction"": ""up"", ""riser"": 0.5,
                ""steps"": [
                    {""corners"": [{""x"":0,""y"":0},{""x"":1,""y"":0},{""x"":1,""y"":0.3},{""x"":0,""y"":0.3}], ""bottom"": 0, ""top"": 0.5},
                    {""corners"": [{""x"":0,""y"":0.3},{""x"":1,""y"":0.3},{""x"":1,""y"":0.6},{""x"":0,""y"":0.6}], ""bottom"": 0, ""top"": 1.0}
                ],
                ""landings"": [{""polygon"": [{""x"":0,""y"":0.6},{""x"":1,""y"":0.6},{""x"":1,""y"":1.6},{""x"":0,""y"":1.6}], ""height"": 1.0}],
                ""railings"": [[{""x"":0,""y"":0,""z"":0.5},{""x"":0,""y"":0.6,""z"":1.0}]],
                ""footprint"": [{""x"":0,""y"":0},{""x"":1,""y"":0},{""x"":1,""y"":1.6},{""x"":0,""y"":1.6}]
            }],
            ""columns"": [{""position"": {""x"": 3, ""y"": 3}, ""size"": 0.3, ""height"": 3.0}],
            ""slabs"": [{
                ""outline"": [{""x"":-1,""y"":-1},{""x"":5,""y"":-1},{""x"":5,""y"":5},{""x"":-1,""y"":5}],
                ""holes"": [[{""x"":0,""y"":0},{""x"":1,""y"":0},{""x"":1,""y"":1.6},{""x"":0,""y"":1.6}]],
                ""thickness"": 0.15
            }]
        }";

        static LevelGeometry Level() => PlanJson.Deserialize<LevelGeometry>(LevelJson);

        static Bounds BoundsOf(MeshData data) => data.ToMesh("test").bounds;

        [Test]
        public void StairsColumnsAndSlabsDeserialize()
        {
            var level = Level();

            Assert.AreEqual(StairDirection.Up, level.Stairs[0].Direction);
            Assert.AreEqual(2, level.Stairs[0].Steps.Count);
            Assert.AreEqual(1.0f, level.Stairs[0].Railings[0][1].Z, 1e-5f);
            Assert.AreEqual(0.3f, level.Columns[0].Size, 1e-5f);
            Assert.AreEqual(1, level.Slabs[0].Holes.Count);
        }

        [Test]
        public void StepsRiseToTheirTops()
        {
            var bounds = BoundsOf(PlanMeshBuilder.Treads(Level().Stairs));

            Assert.AreEqual(0f, bounds.min.y, 1e-4f);
            Assert.AreEqual(1f, bounds.max.y, 1e-4f);
            Assert.AreEqual(1.6f, bounds.max.z, 1e-4f);
        }

        [Test]
        public void RailingsStandAboveTheirLine()
        {
            var bounds = BoundsOf(PlanMeshBuilder.Railings(Level().Stairs));

            Assert.AreEqual(1.0f + 0.9f, bounds.max.y, 0.05f);
            Assert.Greater(bounds.min.y, 0.4f);
        }

        [Test]
        public void SlabHangsBelowTheFloor()
        {
            var bounds = BoundsOf(PlanMeshBuilder.Slabs(Level().Slabs));

            Assert.AreEqual(-0.15f, bounds.min.y, 1e-4f);
            Assert.AreEqual(0f, bounds.max.y, 1e-4f);
        }

        [Test]
        public void HoleIsLeftOutOfTheTriangulation()
        {
            var outer = new[] { new Vector2(0, 0), new Vector2(4, 0), new Vector2(4, 4), new Vector2(0, 4) };
            var hole = new[] { new Vector2(1, 1), new Vector2(3, 1), new Vector2(3, 2), new Vector2(1, 2) };

            var triangles = PolygonTriangulator.Triangulate(outer, new List<IReadOnlyList<Vector2>> { hole }, out var ring);

            var area = 0f;
            for (var i = 0; i < triangles.Count; i += 3)
                area += PolygonTriangulator.SignedArea(new[] { ring[triangles[i]], ring[triangles[i + 1]], ring[triangles[i + 2]] });
            Assert.AreEqual(14f, area, 1e-3f);
            var centre = new Vector2(2f, 1.5f);
            Assert.IsFalse(Enumerable.Range(0, triangles.Count / 3).Any(t =>
                Inside(centre, ring[triangles[t * 3]], ring[triangles[t * 3 + 1]], ring[triangles[t * 3 + 2]])));
        }

        static bool Inside(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            static float Cross(Vector2 u, Vector2 v) => u.x * v.y - u.y * v.x;
            return Cross(b - a, p - a) > 0f && Cross(c - b, p - b) > 0f && Cross(a - c, p - c) > 0f;
        }
    }
}
