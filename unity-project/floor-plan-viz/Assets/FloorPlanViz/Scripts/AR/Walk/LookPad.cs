using UnityEngine;
using UnityEngine.EventSystems;

namespace FloorPlanViz.AR
{
    /// <summary>A screen zone that turns one finger's drag into look movement, in screen pixels.</summary>
    public sealed class LookPad : MonoBehaviour, IPointerDownHandler, IDragHandler, IPointerUpHandler
    {
        const int NoPointer = int.MinValue;

        int pointer = NoPointer;
        Vector2 pending;

        /// <summary>The drag since the last call.</summary>
        public Vector2 TakeDelta()
        {
            var delta = pending;
            pending = Vector2.zero;
            return delta;
        }

        void OnDisable()
        {
            pointer = NoPointer;
            pending = Vector2.zero;
        }

        public void OnPointerDown(PointerEventData eventData)
        {
            if (pointer == NoPointer)
                pointer = eventData.pointerId;
        }

        public void OnDrag(PointerEventData eventData)
        {
            if (eventData.pointerId == pointer)
                pending += eventData.delta;
        }

        public void OnPointerUp(PointerEventData eventData)
        {
            if (eventData.pointerId == pointer)
                pointer = NoPointer;
        }
    }
}
