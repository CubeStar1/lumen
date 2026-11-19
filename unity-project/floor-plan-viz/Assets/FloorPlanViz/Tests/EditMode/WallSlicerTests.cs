using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using FloorPlanViz.Geometry;
using NUnit.Framework;

namespace FloorPlanViz.Tests
{
    public sealed class WallSlicerTests
    {
        const float Tolerance = 1e-4f;

        static WallData Wall(params OpeningData[] openings) => new()
        {
            Start = new PlanPoint { X = 0f, Y = 0f },
            End = new PlanPoint { X = 4f, Y = 0f },
            Thickness = 0.2f,
            Height = 3f,
            Openings = openings.ToList(),
        };

        static OpeningData Door(float offset) =>
            new() { Type = OpeningType.Door, Offset = offset, Width = 0.9f, Sill = 0f, Head = 2.1f };

        static OpeningData Window(float offset) =>
            new() { Type = OpeningType.Window, Offset = offset, Width = 1.2f, Sill = 0.9f, Head = 2.1f };

        [Test]
        public void SolidWallIsOneExtendedPiece()
        {
            var piece = WallSlicer.Slice(Wall()).Single();

            Assert.AreEqual(0f, piece.From, Tolerance);
            Assert.AreEqual(4.2f, piece.To, Tolerance);
            Assert.AreEqual(3f, piece.Height, Tolerance);
        }

        [Test]
        public void DoorLeavesAGapWithALintel()
        {
            var pieces = WallSlicer.Slice(Wall(Door(2f)));

            Assert.AreEqual(3, pieces.Count);
            var lintel = pieces.Single(p => p.Bottom > 0f);
            Assert.AreEqual(2.1f, lintel.Bottom, Tolerance);
            Assert.AreEqual(0.9f, lintel.Length, Tolerance);
            AssertCoversLength(pieces.Where(p => p.Bottom == 0f), 4.2f - 0.9f);
        }

        [Test]
        public void WindowHasSillAndLintel()
        {
            var pieces = WallSlicer.Slice(Wall(Window(2f)));

            Assert.AreEqual(4, pieces.Count);
            Assert.IsTrue(pieces.Any(p => p.Bottom == 0f && System.Math.Abs(p.Top - 0.9f) < Tolerance));
            Assert.IsTrue(pieces.Any(p => System.Math.Abs(p.Bottom - 2.1f) < Tolerance));
        }

        [Test]
        public void AdjacentOpeningsDoNotProduceSlivers()
        {
            var pieces = WallSlicer.Slice(Wall(Window(1f), Window(2.2f)));

            Assert.IsTrue(pieces.All(p => p.Length > 0.005f));
        }

        static void AssertCoversLength(IEnumerable<WallPiece> pieces, float expected) =>
            Assert.AreEqual(expected, pieces.Sum(p => p.Length), Tolerance);
    }
}
