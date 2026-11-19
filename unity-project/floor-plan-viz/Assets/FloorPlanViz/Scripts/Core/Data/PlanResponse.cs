using System.Collections.Generic;

namespace FloorPlanViz.Data
{
    public sealed class PlanResponse
    {
        /// <summary>The backend's building spec, kept as-is so it can be sent back for edits.</summary>
        public object Spec { get; set; }

        public BuildingGeometry Geometry { get; set; }
        public List<string> Warnings { get; set; } = new();
    }
}
