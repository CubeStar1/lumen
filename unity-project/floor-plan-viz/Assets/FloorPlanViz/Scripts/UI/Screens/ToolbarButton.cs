using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>A round glass icon button with a caption, used in the AR toolbar. Active buttons turn solid white.</summary>
    public sealed class ToolbarButton : MonoBehaviour
    {
        [SerializeField] Button button;
        [SerializeField] Image disc;
        [SerializeField] TMP_Text iconText;
        [SerializeField] TMP_Text captionText;

        public event Action Clicked;

        void Awake() => button.onClick.AddListener(() => Clicked?.Invoke());

        public void Set(string icon, string caption, bool active, bool interactable = true)
        {
            iconText.text = icon;
            captionText.text = caption;
            button.interactable = interactable;
            disc.color = active ? Theme.GlassActive : Color.white.WithAlpha(0.18f);
            iconText.color = active ? Theme.Label : Theme.OnGlass;
            var alpha = interactable ? 1f : 0.4f;
            iconText.alpha = alpha;
            captionText.alpha = alpha;
        }
    }
}
