using UnityEngine;

namespace FloorPlanViz.UI
{
    /// <summary>Lifts the bottom of a full-screen panel above the on-screen keyboard.</summary>
    [RequireComponent(typeof(RectTransform))]
    public sealed class KeyboardAvoider : MonoBehaviour
    {
        const float Speed = 14f;

        RectTransform rect;
        Canvas canvas;

        void Awake()
        {
            rect = (RectTransform)transform;
            canvas = GetComponentInParent<Canvas>().rootCanvas;
        }

        void OnDisable() => rect.offsetMin = Vector2.zero;

        void Update()
        {
            var keyboard = TouchScreenKeyboard.visible ? TouchScreenKeyboard.area.height : 0f;
            var target = Mathf.Max(0f, keyboard - Screen.safeArea.yMin) / canvas.scaleFactor;
            var current = Mathf.Lerp(rect.offsetMin.y, target, 1f - Mathf.Exp(-Speed * Time.unscaledDeltaTime));
            rect.offsetMin = new Vector2(0f, Mathf.Abs(current - target) < 0.5f ? target : current);
        }
    }
}
