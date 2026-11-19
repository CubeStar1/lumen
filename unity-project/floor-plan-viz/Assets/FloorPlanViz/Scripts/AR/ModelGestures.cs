using UnityEngine;

namespace FloorPlanViz.AR
{
    /// <summary>Two-finger pinch to scale and twist to rotate the target around its vertical axis.</summary>
    public sealed class ModelGestures : MonoBehaviour
    {
        [SerializeField] float minScale = 0.005f;
        [SerializeField] float maxScale = 1f;

        Transform target;
        float lift;
        bool tracking;
        float startDistance;
        float startAngle;
        float startScale;
        Quaternion startRotation;

        /// <summary>Sets the model to manipulate; <paramref name="baseLift"/> keeps its base resting on the surface as it scales.</summary>
        public void SetTarget(Transform value, float baseLift)
        {
            target = value;
            lift = baseLift;
            tracking = false;
        }

        void Update()
        {
            if (target == null || !ScreenInput.TryGetTwoFingers(out var first, out var second))
            {
                tracking = false;
                return;
            }

            var span = second - first;
            var angle = Mathf.Atan2(span.y, span.x) * Mathf.Rad2Deg;
            if (!tracking)
            {
                tracking = true;
                startDistance = Mathf.Max(span.magnitude, 1f);
                startAngle = angle;
                startScale = target.localScale.x;
                startRotation = target.localRotation;
                return;
            }

            var scale = Mathf.Clamp(startScale * span.magnitude / startDistance, minScale, maxScale);
            target.localScale = Vector3.one * scale;
            target.localPosition = Vector3.up * (lift * scale);
            target.localRotation = startRotation * Quaternion.Euler(0f, startAngle - angle, 0f);
        }
    }
}
