using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    public readonly struct SheetAction
    {
        public readonly string Label;
        public readonly bool Destructive;
        public readonly Action Run;

        public SheetAction(string label, Action run, bool destructive = false)
        {
            Label = label;
            Run = run;
            Destructive = destructive;
        }
    }

    /// <summary>An iOS-style action sheet: a group of choices above a separate Cancel button.</summary>
    public sealed class ActionSheet : AppScreen
    {
        [SerializeField] TMP_Text titleText;
        [SerializeField] RectTransform actionGroup;
        [SerializeField] Button actionTemplate;
        [SerializeField] Button cancelButton;
        [SerializeField] Button dismissArea;

        void Awake()
        {
            cancelButton.onClick.AddListener(() => SetVisible(false));
            dismissArea.onClick.AddListener(() => SetVisible(false));
            actionTemplate.gameObject.SetActive(false);
        }

        public void Show(string title, params SheetAction[] actions)
        {
            titleText.text = title;
            foreach (Transform child in actionGroup)
            {
                if (child != actionTemplate.transform && child != titleText.transform)
                    Destroy(child.gameObject);
            }

            foreach (var action in actions)
            {
                var button = Instantiate(actionTemplate, actionGroup);
                button.gameObject.SetActive(true);
                var label = button.GetComponentInChildren<TMP_Text>();
                label.text = action.Label;
                label.color = action.Destructive ? Theme.Red : Theme.Accent;
                var run = action.Run;
                button.onClick.AddListener(() =>
                {
                    SetVisible(false);
                    run();
                });
            }
            SetVisible(true);
        }
    }
}
