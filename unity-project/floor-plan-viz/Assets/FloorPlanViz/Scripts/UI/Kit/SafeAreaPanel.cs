using UnityEngine;

namespace FloorPlanViz.UI
{
    /// <summary>Keeps a full-screen panel inside the device's safe area (notch, home indicator).</summary>
    [RequireComponent(typeof(RectTransform))]
    public sealed class SafeAreaPanel : MonoBehaviour
    {
        RectTransform rect;
        Rect applied;

        void Awake()
        {
            rect = GetComponent<RectTransform>();
        }

        void Update()
        {
            var area = Screen.safeArea;
            if (area == applied || Screen.width == 0 || Screen.height == 0)
                return;

            applied = area;
            rect.anchorMin = new Vector2(area.xMin / Screen.width, area.yMin / Screen.height);
            rect.anchorMax = new Vector2(area.xMax / Screen.width, area.yMax / Screen.height);
        }
    }
}
