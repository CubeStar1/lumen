using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>An alert with a single text field, such as Rename.</summary>
    public sealed class PromptDialog : AppScreen
    {
        [SerializeField] TMP_Text titleText;
        [SerializeField] TMP_InputField field;
        [SerializeField] Button cancelButton;
        [SerializeField] Button confirmButton;
        [SerializeField] TMP_Text confirmLabel;

        Action<string> confirmed;

        string Value => field.text.Trim();

        void Awake()
        {
            field.shouldHideMobileInput = true;
            cancelButton.onClick.AddListener(() => SetVisible(false));
            confirmButton.onClick.AddListener(Confirm);
            field.onValueChanged.AddListener(_ => confirmButton.interactable = Value.Length > 0);
        }

        public void Show(string title, string value, string confirm, Action<string> onConfirm)
        {
            titleText.text = title;
            confirmLabel.text = confirm;
            field.text = value;
            confirmed = onConfirm;
            SetVisible(true);
            field.ActivateInputField();
        }

        void Confirm()
        {
            if (Value.Length == 0)
                return;
            SetVisible(false);
            confirmed?.Invoke(Value);
        }
    }
}
