using System;

namespace FloorPlanViz.Data
{
    public class PlanSummary
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime UpdatedAt { get; set; }
        public string Kind { get; set; } = "floor";
        public int LevelCount { get; set; } = 1;
        public bool HasImage { get; set; }
        public int RoomCount { get; set; }
        public float Area { get; set; }
        public float Width { get; set; }
        public float Depth { get; set; }
    }

    public sealed class SavedPlan : PlanSummary
    {
        public PlanResponse Plan { get; set; }
    }
}
