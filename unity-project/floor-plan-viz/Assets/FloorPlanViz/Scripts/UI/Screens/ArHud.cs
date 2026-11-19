using System;
using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.AR;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace FloorPlanViz.UI
{
    /// <summary>Floating controls over the camera view: close, coaching hint, place button, the view toolbar and the walking thumbsticks.</summary>
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
        [SerializeField] ToolbarButton explodeButton;
        [SerializeField] ToolbarButton controlsButton;
        [SerializeField] GameObject walkControls;
        [SerializeField] SegmentedControl levelPicker;

        bool roofOn;
        bool labelsOn = true;
        bool explodedOn;
        bool firstPersonOn;
        int levelCount = 1;

        public event Action CloseRequested;
        public event Action PlaceRequested;
        public event Action<bool> RoofToggled;
        public event Action<bool> LabelsToggled;
        public event Action ModeRequested;
        public event Action ResetRequested;
        public event Action EditRequested;
        public event Action<int> LevelSelected;
        public event Action<bool> ExplodeToggled;
        public event Action<bool> FirstPersonToggled;

        void Awake()
        {
            closeButton.onClick.AddListener(() => CloseRequested?.Invoke());
            placeButton.onClick.AddListener(() => PlaceRequested?.Invoke());
            roofButton.Clicked += () => RoofToggled?.Invoke(!roofOn);
            labelsButton.Clicked += () => LabelsToggled?.Invoke(!labelsOn);
            modeButton.Clicked += () => ModeRequested?.Invoke();
            resetButton.Clicked += () => ResetRequested?.Invoke();
            editButton.Clicked += () => EditRequested?.Invoke();
            explodeButton.Clicked += () => ExplodeToggled?.Invoke(!explodedOn);
            controlsButton.Clicked += () => FirstPersonToggled?.Invoke(!firstPersonOn);
            levelPicker.Changed += segment => LevelSelected?.Invoke(levelCount - 1 - segment);
            resetButton.Set(Icons.RestartAlt, "Reset", false);
            editButton.Set(Icons.AutoAwesome, "Edit", false);
        }

        /// <summary>The building's levels, lowest first; the picker lists them top down, like lift buttons.</summary>
        public void SetLevels(IReadOnlyList<string> names, int selected)
        {
            levelCount = names.Count;
            if (levelCount > 1)
                levelPicker.SetSegments(names.Reverse().ToList(), levelCount - 1 - selected);
        }

        public void ShowPlacing(string title)
        {
            titleText.text = title;
            placingControls.SetActive(true);
            toolbar.SetActive(false);
            walkControls.SetActive(false);
            levelPicker.gameObject.SetActive(false);
            SetPlaceReady(false);
        }

        public void SetPlaceReady(bool ready)
        {
            placeButton.interactable = ready;
            placeGroup.alpha = ready ? 1f : 0.45f;
            SetHint(ready ? "Tap Place, or tap a spot on the surface." : "Move slowly to find a flat surface.");
        }

        public void ShowPlaced(ViewMode mode, bool roof, bool labels, bool exploded, bool firstPerson)
        {
            placingControls.SetActive(false);
            toolbar.SetActive(true);
            roofOn = roof;
            labelsOn = labels;
            explodedOn = exploded;
            firstPersonOn = firstPerson;
            var tabletop = mode == ViewMode.Tabletop;
            var building = levelCount > 1;
            levelPicker.gameObject.SetActive(building);
            explodeButton.gameObject.SetActive(building && tabletop);
            roofButton.gameObject.SetActive(tabletop);
            resetButton.gameObject.SetActive(tabletop);
            controlsButton.gameObject.SetActive(!tabletop);
            walkControls.SetActive(!tabletop && firstPerson);
            explodeButton.Set(Icons.Layers, "Explode", exploded);
            roofButton.Set(Icons.Roofing, "Roof", roof);
            labelsButton.Set(Icons.Label, "Labels", labels);
            modeButton.Set(tabletop ? Icons.Walk : Icons.ViewInAr, tabletop ? "Walk in" : "Model", false);
            controlsButton.Set(Icons.Gamepad, "Controls", firstPerson);
        }

        public void SetHint(string hint)
        {
            hintPill.SetActive(!string.IsNullOrEmpty(hint));
            if (hintText.text != hint)
                hintText.text = hint;
        }
    }
}
