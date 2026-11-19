using UnityEngine;
using UnityEngine.EventSystems;

namespace FloorPlanViz.AR
{
    /// <summary>A floating thumbstick: it jumps to wherever a finger lands in its zone and follows the finger past its rim.</summary>
    public sealed class VirtualJoystick : MonoBehaviour, IPointerDownHandler, IDragHandler, IPointerUpHandler
    {
        const int NoPointer = int.MinValue;
        const float DeadZone = 0.12f;
        const float RestAlpha = 0.5f;

        [SerializeField] RectTransform stick;
        [SerializeField] RectTransform knob;
        [SerializeField] CanvasGroup group;

        Vector2 restPosition;
        int pointer = NoPointer;

        /// <summary>Stick deflection, with each axis in [-1, 1] and length at most 1.</summary>
        public Vector2 Value { get; private set; }

        void Awake()
        {
            restPosition = stick.anchoredPosition;
            group.alpha = RestAlpha;
        }

        void OnDisable() => Release();

        public void OnPointerDown(PointerEventData eventData)
        {
            if (pointer != NoPointer)
                return;
            pointer = eventData.pointerId;
            stick.position = eventData.position;
            group.alpha = 1f;
            Track(eventData.position);
        }

        public void OnDrag(PointerEventData eventData)
        {
            if (eventData.pointerId == pointer)
                Track(eventData.position);
        }

        public void OnPointerUp(PointerEventData eventData)
        {
            if (eventData.pointerId == pointer)
                Release();
        }

        void Track(Vector2 finger)
        {
            var radius = stick.rect.width * 0.5f * stick.lossyScale.x;
            var offset = finger - (Vector2)stick.position;
            if (offset.magnitude > radius)
            {
                stick.position = finger - offset.normalized * radius;
                offset = offset.normalized * radius;
            }
            knob.position = (Vector2)stick.position + offset;
            var deflection = offset / radius;
            Value = deflection.magnitude < DeadZone ? Vector2.zero : deflection;
        }

        void Release()
        {
            pointer = NoPointer;
            Value = Vector2.zero;
            if (stick == null)
                return;
            stick.anchoredPosition = restPosition;
            knob.anchoredPosition = Vector2.zero;
            group.alpha = RestAlpha;
        }
    }
}
