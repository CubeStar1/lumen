using System.Collections.Generic;
using UnityEngine;

namespace FloorPlanViz.Data
{
    public sealed class PlanGeometry
    {
        public PlanBounds Bounds { get; set; }
        public List<RoomData> Rooms { get; set; } = new();
        public List<WallData> Walls { get; set; } = new();
    }

    public sealed class PlanBounds
    {
        public PlanPoint Min { get; set; }
        public PlanPoint Max { get; set; }

        public Vector2 Size => Max.ToVector2() - Min.ToVector2();
    }

    public sealed class RoomData
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public RoomType Type { get; set; }
        public List<PlanPoint> Polygon { get; set; } = new();
        public PlanPoint Centroid { get; set; }
        public float Area { get; set; }
    }

    public sealed class WallData
    {
        public string Id { get; set; }
        public PlanPoint Start { get; set; }
        public PlanPoint End { get; set; }
        public float Thickness { get; set; }
        public float Height { get; set; }
        public bool Exterior { get; set; }
        public List<OpeningData> Openings { get; set; } = new();
    }

    public sealed class OpeningData
    {
        public string Id { get; set; }
        public OpeningType Type { get; set; }
        public float Offset { get; set; }
        public float Width { get; set; }
        public float Sill { get; set; }
        public float Head { get; set; }
    }
}
