using System.Collections.Generic;

namespace FloorPlanViz.Data
{
    public sealed class PlanResponse
    {
        public PlanSpec Spec { get; set; }
        public PlanGeometry Geometry { get; set; }
        public List<string> Warnings { get; set; } = new();
    }
}
