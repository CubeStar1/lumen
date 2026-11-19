using System;

namespace FloorPlanViz.Api
{
    /// <summary>A backend failure with a message that can be shown to the user.</summary>
    public sealed class PlanApiException : Exception
    {
        public PlanApiException(string message) : base(message) { }
    }
}
