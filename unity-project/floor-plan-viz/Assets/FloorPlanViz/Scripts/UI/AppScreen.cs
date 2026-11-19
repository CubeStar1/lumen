using UnityEngine;

namespace FloorPlanViz.UI
{
    /// <summary>A page or overlay that fades in, optionally sliding a panel into place as it does.</summary>
    [RequireComponent(typeof(CanvasGroup))]
    public abstract class AppScreen : MonoBehaviour
    {
        const float ShowSeconds = 0.22f;

        [SerializeField] RectTransform slidingPanel;
        [SerializeField] Vector2 slideFrom;

        CanvasGroup group;
        Vector2 restingPosition;
        bool hasRestingPosition;
        float progress = 1f;

        public bool IsVisible => gameObject.activeSelf;

        public void SetVisible(bool visible)
        {
            if (visible == gameObject.activeSelf)
                return;
            gameObject.SetActive(visible);
            if (visible)
            {
                progress = 0f;
                Animate(0f);
            }
        }

        protected virtual void Update()
        {
            if (progress >= 1f)
                return;
            progress = Mathf.Min(1f, progress + Time.unscaledDeltaTime / ShowSeconds);
            Animate(1f - Mathf.Pow(1f - progress, 3f));
        }

        void Animate(float amount)
        {
            if (group == null)
                group = GetComponent<CanvasGroup>();
            group.alpha = amount;
            if (slidingPanel == null)
                return;
            if (!hasRestingPosition)
            {
                restingPosition = slidingPanel.anchoredPosition;
                hasRestingPosition = true;
            }
            slidingPanel.anchoredPosition = restingPosition + slideFrom * (1f - amount);
        }
    }
}
