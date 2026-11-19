using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Shrinks a control slightly while it is pressed.</summary>
    public sealed class PressFeedback : MonoBehaviour, IPointerDownHandler, IPointerUpHandler, IPointerExitHandler
    {
        const float PressedScale = 0.96f;
        const float Speed = 18f;

        Selectable selectable;
        float target = 1f;

        void Awake() => selectable = GetComponent<Selectable>();

        void OnDisable()
        {
            target = 1f;
            transform.localScale = Vector3.one;
        }

        public void OnPointerDown(PointerEventData _)
        {
            if (selectable == null || selectable.IsInteractable())
                target = PressedScale;
        }

        public void OnPointerUp(PointerEventData _) => target = 1f;

        public void OnPointerExit(PointerEventData _) => target = 1f;

        void Update()
        {
            var scale = Mathf.Lerp(transform.localScale.x, target, 1f - Mathf.Exp(-Speed * Time.unscaledDeltaTime));
            transform.localScale = Vector3.one * scale;
        }
    }
}
