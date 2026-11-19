using UnityEngine;
using UnityEngine.InputSystem;

namespace FloorPlanViz.Debugging
{
    /// <summary>Mouse orbit camera for inspecting a plan on desktop: drag to orbit, scroll to zoom.</summary>
    public sealed class OrbitCamera : MonoBehaviour
    {
        [SerializeField] float yaw = 30f;
        [SerializeField] float pitch = 55f;
        [SerializeField] float distance = 15f;
        [SerializeField] float orbitSpeed = 0.25f;
        [SerializeField] float zoomSpeed = 0.002f;

        public void Frame(float size)
        {
            distance = size * 1.4f;
            Apply();
        }

        void LateUpdate()
        {
            var mouse = Mouse.current;
            if (mouse == null)
                return;

            if (mouse.leftButton.isPressed || mouse.rightButton.isPressed)
            {
                var delta = mouse.delta.ReadValue() * orbitSpeed;
                yaw += delta.x;
                pitch = Mathf.Clamp(pitch - delta.y, 5f, 89f);
            }
            distance = Mathf.Max(1f, distance * (1f - mouse.scroll.ReadValue().y * zoomSpeed));
            Apply();
        }

        void Apply()
        {
            var rotation = Quaternion.Euler(pitch, yaw, 0f);
            transform.SetPositionAndRotation(rotation * new Vector3(0f, 0f, -distance), rotation);
        }
    }
}
