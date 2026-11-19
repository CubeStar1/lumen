using System.Globalization;
using TMPro;
using UnityEngine;

namespace FloorPlanViz.Model
{
    /// <summary>A world-space room name on a rounded card that always faces the camera.</summary>
    [RequireComponent(typeof(TextMeshPro))]
    public sealed class RoomLabel : MonoBehaviour
    {
        [SerializeField] SpriteRenderer background;
        [SerializeField] Vector2 padding = new(0.5f, 0.3f);

        TextMeshPro text;

        void Awake()
        {
            text = GetComponent<TextMeshPro>();
        }

        public void Show(string name, float area, Vector3 localPosition)
        {
            text.text = $"{TitleCase(name)}\n<size=70%><color=#6E6E73>{area:0.#} m²</color></size>";
            transform.localPosition = localPosition;
            text.ForceMeshUpdate();
            background.size = (Vector2)text.textBounds.size + padding;
            background.transform.localPosition = new Vector3(text.textBounds.center.x, text.textBounds.center.y, 0.01f);
        }

        public static string TitleCase(string value) =>
            CultureInfo.InvariantCulture.TextInfo.ToTitleCase(value.Trim().ToLowerInvariant());

        void LateUpdate()
        {
            var camera = Camera.main;
            if (camera == null)
                return;
            var viewer = camera.transform;
            transform.rotation = Quaternion.LookRotation(transform.position - viewer.position, viewer.up);
        }
    }
}
