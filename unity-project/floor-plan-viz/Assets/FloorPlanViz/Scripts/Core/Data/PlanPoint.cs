using UnityEngine;

namespace FloorPlanViz.Data
{
    public sealed class PlanPoint
    {
        public float X { get; set; }
        public float Y { get; set; }

        public Vector2 ToVector2() => new(X, Y);

        public Vector3 ToWorld(float height = 0f) => new(X, height, Y);
    }
}
