using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.EnhancedTouch;
using Touch = UnityEngine.InputSystem.EnhancedTouch.Touch;

namespace FloorPlanViz.AR
{
    /// <summary>Taps and two-finger gestures on the AR view, ignoring touches that land on UI.</summary>
    public static class ScreenInput
    {
        static readonly List<RaycastResult> UiHits = new();

        public static void Enable() => EnhancedTouchSupport.Enable();

        public static bool TryGetTap(out Vector2 position)
        {
            foreach (var touch in Touch.activeTouches)
            {
                if (touch.phase == UnityEngine.InputSystem.TouchPhase.Ended && touch.isTap && !IsOverUi(touch.screenPosition))
                {
                    position = touch.screenPosition;
                    return true;
                }
            }

            var mouse = Mouse.current;
            if (mouse != null && mouse.leftButton.wasReleasedThisFrame && !IsOverUi(mouse.position.ReadValue()))
            {
                position = mouse.position.ReadValue();
                return true;
            }

            position = default;
            return false;
        }

        public static bool TryGetTwoFingers(out Vector2 first, out Vector2 second)
        {
            if (Touch.activeTouches.Count == 2)
            {
                first = Touch.activeTouches[0].screenPosition;
                second = Touch.activeTouches[1].screenPosition;
                return true;
            }
            first = second = default;
            return false;
        }

        static bool IsOverUi(Vector2 screenPosition)
        {
            var eventSystem = EventSystem.current;
            if (eventSystem == null)
                return false;
            UiHits.Clear();
            eventSystem.RaycastAll(new PointerEventData(eventSystem) { position = screenPosition }, UiHits);
            return UiHits.Count > 0;
        }
    }
}
