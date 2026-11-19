using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Scales the canvas so one UI unit is roughly one iOS point on every device. Off device (Editor),
    /// the screen shape decides whether to preview as a phone or a tablet.</summary>
    [RequireComponent(typeof(CanvasScaler))]
    public sealed class DensityScaler : MonoBehaviour
    {
        const float PhonePointsPerInch = 153f;
        const float TabletPointsPerInch = 132f;
        const float PhoneShortSide = 390f;
        const float TabletShortSide = 820f;
        const float PhoneAspect = 1.7f;

        CanvasScaler scaler;

        void Awake()
        {
            scaler = GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ConstantPixelSize;
        }

        void Update()
        {
            var scale = CurrentScale();
            if (!Mathf.Approximately(scale, scaler.scaleFactor))
                scaler.scaleFactor = scale;
        }

        static float CurrentScale()
        {
            if (Application.isMobilePlatform && Screen.dpi > 0f)
            {
                var pointsPerInch = SystemInfo.deviceModel.StartsWith("iPad") ? TabletPointsPerInch : PhonePointsPerInch;
                return Screen.dpi / pointsPerInch;
            }
            var shortSide = Mathf.Min(Screen.width, Screen.height);
            var isPhoneShaped = Mathf.Max(Screen.width, Screen.height) / shortSide > PhoneAspect;
            return Mathf.Max(0.5f, shortSide / (isPhoneShaped ? PhoneShortSide : TabletShortSide));
        }
    }
}
