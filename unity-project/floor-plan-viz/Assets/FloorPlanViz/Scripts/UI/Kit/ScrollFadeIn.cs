using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Fades a navigation bar title in once the page's large title has scrolled away.</summary>
    public sealed class ScrollFadeIn : MonoBehaviour
    {
        [SerializeField] ScrollRect scroll;
        [SerializeField] CanvasGroup target;
        [SerializeField] float threshold = 36f;
        [SerializeField] float range = 16f;

        void LateUpdate() => target.alpha = Mathf.Clamp01((scroll.content.anchoredPosition.y - threshold) / range);
    }
}
