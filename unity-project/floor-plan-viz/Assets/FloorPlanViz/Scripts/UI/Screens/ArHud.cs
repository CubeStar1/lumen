using System;
using FloorPlanViz.AR;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Floating controls over the camera view: close, coaching hint, place button and the view toolbar.</summary>
    public sealed class ArHud : AppScreen
    {
        [SerializeField] Button closeButton;
        [SerializeField] TMP_Text titleText;
        [SerializeField] GameObject hintPill;
        [SerializeField] TMP_Text hintText;
        [SerializeField] GameObject placingControls;
        [SerializeField] Button placeButton;
        [SerializeField] CanvasGroup placeGroup;
        [SerializeField] GameObject toolbar;
        [SerializeField] ToolbarButton roofButton;
        [SerializeField] ToolbarButton labelsButton;
        [SerializeField] ToolbarButton modeButton;
        [SerializeField] ToolbarButton resetButton;
        [SerializeField] ToolbarButton editButton;

        bool roofOn;
        bool labelsOn = true;

        public event Action CloseRequested;
        public event Action PlaceRequested;
        public event Action<bool> RoofToggled;
        public event Action<bool> LabelsToggled;
        public event Action ModeRequested;
        public event Action ResetRequested;
        public event Action EditRequested;

        void Awake()
        {
            closeButton.onClick.AddListener(() => CloseRequested?.Invoke());
            placeButton.onClick.AddListener(() => PlaceRequested?.Invoke());
            roofButton.Clicked += () => RoofToggled?.Invoke(!roofOn);
            labelsButton.Clicked += () => LabelsToggled?.Invoke(!labelsOn);
            modeButton.Clicked += () => ModeRequested?.Invoke();
            resetButton.Clicked += () => ResetRequested?.Invoke();
            editButton.Clicked += () => EditRequested?.Invoke();
            resetButton.Set(Icons.RestartAlt, "Reset", false);
            editButton.Set(Icons.AutoAwesome, "Edit", false);
        }

        public void ShowPlacing(string title)
        {
            titleText.text = title;
            placingControls.SetActive(true);
            toolbar.SetActive(false);
            SetPlaceReady(false);
        }

        public void SetPlaceReady(bool ready)
        {
            placeButton.interactable = ready;
            placeGroup.alpha = ready ? 1f : 0.45f;
            SetHint(ready ? "Tap Place, or tap a spot on the surface." : "Move slowly to find a flat surface.");
        }

        public void ShowPlaced(ViewMode mode, bool roof, bool labels)
        {
            placingControls.SetActive(false);
            toolbar.SetActive(true);
            roofOn = roof;
            labelsOn = labels;
            var tabletop = mode == ViewMode.Tabletop;
            roofButton.Set(Icons.Roofing, "Roof", roof, interactable: tabletop);
            labelsButton.Set(Icons.Label, "Labels", labels);
            modeButton.Set(tabletop ? Icons.Walk : Icons.ViewInAr, tabletop ? "Walk in" : "Model", false);
            resetButton.Set(Icons.RestartAlt, "Reset", false, interactable: tabletop);
        }

        public void SetHint(string hint)
        {
            hintPill.SetActive(!string.IsNullOrEmpty(hint));
            if (hintText.text != hint)
                hintText.text = hint;
        }
    }
}
