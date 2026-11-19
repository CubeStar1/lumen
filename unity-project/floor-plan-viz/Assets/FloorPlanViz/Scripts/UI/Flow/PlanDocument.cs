using FloorPlanViz.Data;

namespace FloorPlanViz.UI
{
    /// <summary>The plan the user is looking at: a saved plan from the server, or the bundled sample.</summary>
    public sealed class PlanDocument
    {
        public string Id { get; }
        public string Name { get; set; }
        public PlanResponse Plan { get; set; }

        public bool IsSaved => Id != null;

        PlanDocument(string id, string name, PlanResponse plan)
        {
            Id = id;
            Name = name;
            Plan = plan;
        }

        public static PlanDocument From(SavedPlan saved) => new(saved.Id, saved.Name, saved.Plan);

        public static PlanDocument Sample(PlanResponse plan) => new(null, "Sample apartment", plan);
    }
}
