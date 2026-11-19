using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Bottom sheet where the user describes a change to the plan in plain language.</summary>
    public sealed class EditSheet : AppScreen
    {
        [SerializeField] TMP_InputField instructionField;
        [SerializeField] Button applyButton;
        [SerializeField] Button cancelButton;
        [SerializeField] Button dismissArea;
        [SerializeField] Button[] suggestions;

        public event Action<string> Submitted;
        public event Action Cancelled;

        string Instruction => instructionField.text.Trim();

        void Awake()
        {
            applyButton.onClick.AddListener(Submit);
            cancelButton.onClick.AddListener(() => Cancelled?.Invoke());
            dismissArea.onClick.AddListener(() => Cancelled?.Invoke());
            instructionField.onValueChanged.AddListener(_ => applyButton.interactable = Instruction.Length > 0);
            instructionField.shouldHideMobileInput = true;
            foreach (var suggestion in suggestions)
            {
                var text = suggestion.GetComponentInChildren<TMP_Text>().text;
                suggestion.onClick.AddListener(() => instructionField.text = text);
            }
        }

        public void Show()
        {
            instructionField.text = "";
            applyButton.interactable = false;
            SetVisible(true);
        }

        void Submit()
        {
            if (Instruction.Length > 0)
                Submitted?.Invoke(Instruction);
        }
    }
}
