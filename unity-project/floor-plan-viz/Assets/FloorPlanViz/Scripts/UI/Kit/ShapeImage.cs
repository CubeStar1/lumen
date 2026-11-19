using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>An Image used as a background shape. Unlike Image, it never asks layout for space,
    /// so a rounded sprite's borders don't inflate the size of the element it fills.</summary>
    [RequireComponent(typeof(CanvasRenderer))]
    public sealed class ShapeImage : Image
    {
        public override float minWidth => 0f;
        public override float preferredWidth => 0f;
        public override float flexibleWidth => -1f;
        public override float minHeight => 0f;
        public override float preferredHeight => 0f;
        public override float flexibleHeight => -1f;
    }
}
