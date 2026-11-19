using System.Collections.Generic;
using FloorPlanViz.Geometry;
using NUnit.Framework;
using UnityEngine;

namespace FloorPlanViz.Tests
{
    public sealed class PolygonTriangulatorTests
    {
        static float TriangulatedArea(IReadOnlyList<Vector2> polygon, List<int> triangles)
        {
            var area = 0f;
            for (var i = 0; i < triangles.Count; i += 3)
            {
                var triangle = new[] { polygon[triangles[i]], polygon[triangles[i + 1]], polygon[triangles[i + 2]] };
                var signed = PolygonTriangulator.SignedArea(triangle);
                Assert.Greater(signed, 0f, "triangles must be counter-clockwise");
                area += signed;
            }
            return area;
        }

        [Test]
        public void SquareBecomesTwoTriangles()
        {
            var square = new[] { new Vector2(0, 0), new Vector2(2, 0), new Vector2(2, 2), new Vector2(0, 2) };

            var triangles = PolygonTriangulator.Triangulate(square);

            Assert.AreEqual(6, triangles.Count);
            Assert.AreEqual(4f, TriangulatedArea(square, triangles), 1e-4f);
        }

        [Test]
        public void ClockwiseInputIsHandled()
        {
            var square = new[] { new Vector2(0, 0), new Vector2(0, 2), new Vector2(2, 2), new Vector2(2, 0) };

            Assert.AreEqual(4f, TriangulatedArea(square, PolygonTriangulator.Triangulate(square)), 1e-4f);
        }

        [Test]
        public void ConcaveLShapeKeepsItsArea()
        {
            var shape = new[]
            {
                new Vector2(0, 0), new Vector2(6, 0), new Vector2(6, 2),
                new Vector2(3, 2), new Vector2(3, 5), new Vector2(0, 5),
            };

            Assert.AreEqual(21f, TriangulatedArea(shape, PolygonTriangulator.Triangulate(shape)), 1e-4f);
        }

        [Test]
        public void CollinearVerticesAreSkipped()
        {
            var shape = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(2, 0), new Vector2(2, 2), new Vector2(0, 2) };

            var triangles = PolygonTriangulator.Triangulate(shape);

            Assert.AreEqual(4f, TriangulatedArea(shape, triangles), 1e-4f);
        }
    }
}
