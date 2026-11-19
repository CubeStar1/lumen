using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using UnityEngine;

namespace FloorPlanViz.Geometry
{
    /// <summary>A solid block of wall, measured along the wall from its extended start.</summary>
    public readonly struct WallPiece
    {
        public readonly float From;
        public readonly float To;
        public readonly float Bottom;
        public readonly float Top;

        public WallPiece(float from, float to, float bottom, float top)
        {
            From = from;
            To = to;
            Bottom = bottom;
            Top = top;
        }

        public float Length => To - From;
        public float Height => Top - Bottom;
    }

    /// <summary>
    /// Splits a wall into solid blocks around its openings. Walls are extended by half their
    /// thickness at both ends so that corners close without mitring.
    /// </summary>
    public static class WallSlicer
    {
        const float MinSize = 0.005f;

        public static float ExtendedLength(WallData wall) =>
            Vector2.Distance(wall.Start.ToVector2(), wall.End.ToVector2()) + wall.Thickness;

        public static List<WallPiece> Slice(WallData wall)
        {
            var pieces = new List<WallPiece>();
            var shift = wall.Thickness / 2f;
            var cursor = 0f;

            foreach (var opening in wall.Openings.OrderBy(o => o.Offset))
            {
                var from = opening.Offset - opening.Width / 2f + shift;
                var to = from + opening.Width;
                Add(pieces, cursor, from, 0f, wall.Height);
                Add(pieces, from, to, 0f, opening.Sill);
                Add(pieces, from, to, opening.Head, wall.Height);
                cursor = to;
            }

            Add(pieces, cursor, ExtendedLength(wall), 0f, wall.Height);
            return pieces;
        }

        static void Add(List<WallPiece> pieces, float from, float to, float bottom, float top)
        {
            if (to - from > MinSize && top - bottom > MinSize)
                pieces.Add(new WallPiece(from, to, bottom, top));
        }
    }
}
