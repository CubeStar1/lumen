using TMPro;
using UnityEngine;

namespace FloorPlanViz.UI
{
    public enum ToastKind
    {
        Success,
        Error,
    }

    /// <summary>A short message banner at the top of the screen that hides itself.</summary>
    public sealed class Toast : AppScreen
    {
        const float SecondsPerCharacter = 0.05f;
        const float MinSeconds = 2.5f;
        const float MaxSeconds = 7f;

        [SerializeField] TMP_Text iconText;
        [SerializeField] TMP_Text messageText;

        float hideAt;

        public void Show(string message, ToastKind kind)
        {
            iconText.text = kind == ToastKind.Error ? Icons.Error : Icons.CheckCircle;
            iconText.color = kind == ToastKind.Error ? Theme.Red : Theme.Green;
            messageText.text = message;
            hideAt = Time.unscaledTime + Mathf.Clamp(message.Length * SecondsPerCharacter, MinSeconds, MaxSeconds);
            SetVisible(false);
            SetVisible(true);
        }

        protected override void Update()
        {
            base.Update();
            if (Time.unscaledTime > hideAt)
                SetVisible(false);
        }
    }
}
