using FloorPlanViz.Api;
using FloorPlanViz.Data;
using FloorPlanViz.Model;
using UnityEngine;

namespace FloorPlanViz.Debugging
{
    /// <summary>Builds a saved plan response on start so geometry can be inspected without AR.</summary>
    public sealed class DebugPlanLoader : MonoBehaviour
    {
        [SerializeField] FloorPlanBuilder builder;
        [SerializeField] OrbitCamera orbitCamera;
        [SerializeField] TextAsset plan;
        [SerializeField] bool showRoof;

        void Start()
        {
            var response = PlanJson.Deserialize<PlanResponse>(plan.text);
            var model = builder.Build(response.Geometry, transform);
            model.RoofVisible = showRoof;
            orbitCamera.Frame(model.Footprint);
        }
    }
}
