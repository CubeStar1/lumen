using System.Collections;
using FloorPlanViz.Model;
using UnityEngine;

namespace FloorPlanViz.AR
{
    public enum ViewMode
    {
        Tabletop,
        Walkthrough,
    }

    /// <summary>Switches a placed model between a scaled tabletop miniature and a life-size walkthrough.</summary>
    public sealed class ViewModeController : MonoBehaviour
    {
        const float WalkthroughLabelHeight = 2.3f;
        const float AppearSeconds = 0.45f;

        [SerializeField] float tabletopSize = 0.6f;
        [SerializeField] Transform viewer;
        [SerializeField] ModelGestures gestures;

        Coroutine appearing;

        public ViewMode Mode { get; private set; }

        public void ShowTabletop(FloorPlanModel model, bool animate = true)
        {
            Mode = ViewMode.Tabletop;
            model.BaseVisible = true;
            model.LabelHeight = null;

            var target = model.transform;
            var scale = tabletopSize / model.Footprint;
            target.localRotation = Quaternion.identity;
            target.localPosition = Vector3.up * (model.BaseThickness * scale);
            gestures.SetTarget(target, model.BaseThickness);

            if (appearing != null)
                StopCoroutine(appearing);
            if (animate)
                appearing = StartCoroutine(Appear(target, scale, model.BaseThickness));
            else
                target.localScale = Vector3.one * scale;
        }

        /// <summary>Shows the model at full size with the viewer standing in its largest room.</summary>
        public void ShowWalkthrough(FloorPlanModel model, float floorHeight)
        {
            Mode = ViewMode.Walkthrough;
            if (appearing != null)
                StopCoroutine(appearing);
            gestures.SetTarget(null, 0f);
            model.RoofVisible = false;
            model.BaseVisible = false;
            model.LabelHeight = WalkthroughLabelHeight;

            var target = model.transform;
            target.localScale = Vector3.one;
            var forward = Vector3.ProjectOnPlane(viewer.forward, Vector3.up);
            target.rotation = Quaternion.LookRotation(forward.sqrMagnitude > 1e-4f ? forward : Vector3.forward);

            var feet = new Vector3(viewer.position.x, floorHeight, viewer.position.z);
            target.position = feet - target.rotation * model.MainRoomCentre;
        }

        static IEnumerator Appear(Transform target, float scale, float baseThickness)
        {
            for (var t = 0f; t < 1f; t += Time.deltaTime / AppearSeconds)
            {
                if (target == null)
                    yield break;
                var current = scale * EaseOutBack(t);
                target.localScale = Vector3.one * current;
                target.localPosition = Vector3.up * (baseThickness * current);
                yield return null;
            }
            if (target == null)
                yield break;
            target.localScale = Vector3.one * scale;
            target.localPosition = Vector3.up * (baseThickness * scale);
        }

        static float EaseOutBack(float t)
        {
            const float overshoot = 1.4f;
            var x = t - 1f;
            return 1f + x * x * ((overshoot + 1f) * x + overshoot);
        }
    }
}
