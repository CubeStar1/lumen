using System.Collections.Generic;
using System.Linq;

namespace FloorPlanViz.Data
{
    /// <summary>What to read from the picked images.</summary>
    public enum ParseKind
    {
        Floor,
        Sheet,
        Photos,
    }

    public enum JobState
    {
        Running,
        Done,
        Failed,
    }

    public enum StageState
    {
        Pending,
        Running,
        Done,
    }

    public sealed class JobStage
    {
        public string Name { get; set; }
        public StageState State { get; set; }
    }

    /// <summary>A parse running on the server, with the stages it reports as it works.</summary>
    public sealed class ParseJob
    {
        public string Id { get; set; }
        public JobState State { get; set; }
        public List<JobStage> Stages { get; set; } = new();
        public string PlanId { get; set; }
        public string Error { get; set; }
        public string Stage { get; set; }
        public float Progress { get; set; }

        public int StagesDone => Stages.Count(s => s.State == StageState.Done);
    }
}
