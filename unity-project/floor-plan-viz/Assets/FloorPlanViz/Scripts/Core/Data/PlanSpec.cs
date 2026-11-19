using System.Collections.Generic;

namespace FloorPlanViz.Data
{
    public sealed class PlanSpec
    {
        public float WallHeight { get; set; }
        public List<RoomSpec> Rooms { get; set; } = new();
        public List<OpeningSpec> Openings { get; set; } = new();
        public string Notes { get; set; } = "";
    }

    public sealed class RoomSpec
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public RoomType Type { get; set; }
        public List<PlanPoint> Polygon { get; set; } = new();
    }

    public sealed class OpeningSpec
    {
        public string Id { get; set; }
        public OpeningType Type { get; set; }
        public List<string> Rooms { get; set; } = new();
        public PlanPoint Position { get; set; }
        public float Width { get; set; }
    }
}
