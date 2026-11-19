using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>A centred card with a spinner, the current stage of the work and how long it has taken.</summary>
    public sealed class ProcessingOverlay : AppScreen
    {
        const float SecondsPerStage = 9f;

        [SerializeField] TMP_Text titleText;
        [SerializeField] TMP_Text stageText;
        [SerializeField] TMP_Text elapsedText;
        [SerializeField] Button cancelButton;

        string[] stages = Array.Empty<string>();
        string reported;
        float startedAt;

        public event Action Cancelled;

        void Awake() => cancelButton.onClick.AddListener(() => Cancelled?.Invoke());

        public void Show(string title, string[] workStages)
        {
            titleText.text = title;
            stages = workStages ?? Array.Empty<string>();
            reported = null;
            startedAt = Time.unscaledTime;
            SetVisible(true);
            Refresh();
        }

        /// <summary>Shows the stage the work reports, in place of the timed stages.</summary>
        public void Report(string stage) => reported = stage;

        protected override void Update()
        {
            base.Update();
            Refresh();
        }

        void Refresh()
        {
            var elapsed = Time.unscaledTime - startedAt;
            var stage = reported ?? (stages.Length == 0 ? "" : stages[Mathf.Min((int)(elapsed / SecondsPerStage), stages.Length - 1)]);
            if (stageText.text != stage)
                stageText.text = stage;
            elapsedText.text = elapsed < 2f ? "" : $"{elapsed:0} s";
        }
    }
}
