using System;
using System.Linq;
using FloorPlanViz.AR;
using FloorPlanViz.Data;
using FloorPlanViz.Model;
using UnityEngine;
using UnityEngine.XR.ARFoundation;

namespace FloorPlanViz.UI
{
    /// <summary>The AR part of the app: runs the session, places the model and drives the HUD.</summary>
    public sealed class ArExperience : MonoBehaviour
    {
        const string PlacedHint = "Pinch to resize · Twist to rotate · Tap to move";

        [SerializeField] ARSession session;
        [SerializeField] FloorPlanBuilder builder;
        [SerializeField] PlacementController placement;
        [SerializeField] ViewModeController viewMode;
        [SerializeField] ArHud hud;

        FloorPlanModel model;
        int level;
        bool firstPerson = true;

        public event Action CloseRequested;
        public event Action EditRequested;

        public bool IsActive => model != null;

        /// <summary>The index of the level picked in the HUD, as the backend numbers it.</summary>
        public int SelectedLevel => model.Levels[level].Index;

        void Awake()
        {
            placement.Placed += OnPlaced;
            hud.CloseRequested += () => CloseRequested?.Invoke();
            hud.EditRequested += () => EditRequested?.Invoke();
            hud.PlaceRequested += () => placement.PlaceAtReticle();
            hud.RoofToggled += visible =>
            {
                model.RoofVisible = visible;
                RefreshToolbar();
            };
            hud.LabelsToggled += visible =>
            {
                model.LabelsVisible = visible;
                RefreshToolbar();
            };
            hud.ModeRequested += ToggleMode;
            hud.ResetRequested += () => viewMode.ShowTabletop(model);
            hud.LevelSelected += SelectLevel;
            hud.ExplodeToggled += exploded =>
            {
                model.Exploded = exploded;
                RefreshToolbar();
            };
            hud.FirstPersonToggled += on =>
            {
                firstPerson = on;
                ShowWalkthrough();
                RefreshToolbar();
            };
        }

        void Update()
        {
            if (model != null && !placement.IsPlaced && hud.IsVisible)
                hud.SetPlaceReady(placement.ReticleOnSurface);
        }

        public void Enter(PlanDocument document)
        {
            session.enabled = true;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            model = builder.Build(document.Plan.Geometry, null);
            level = model.Levels.Count - 1;
            hud.SetLevels(model.Levels.Select(l => Format.LevelLabel(l.Name)).ToList(), level);
            placement.Begin(model);
            hud.ShowPlacing(document.Name);
        }

        public void Exit()
        {
            viewMode.StopWalking();
            placement.Clear();
            if (model != null)
                Destroy(model.gameObject);
            model = null;
            session.enabled = false;
            Screen.sleepTimeout = SleepTimeout.SystemSetting;
        }

        /// <summary>Swaps in an edited plan, keeping the placement, view mode and toggles.</summary>
        public void Rebuild(PlanResponse plan)
        {
            var parent = model.transform.parent;
            var wasPlaced = placement.IsPlaced;
            var labelsVisible = model.LabelsVisible;
            var roofVisible = model.RoofVisible;
            var exploded = model.Exploded;
            var local = (model.transform.localPosition, model.transform.localRotation, model.transform.localScale);
            Destroy(model.gameObject);

            model = builder.Build(plan.Geometry, parent);
            model.LabelsVisible = labelsVisible;
            level = Mathf.Min(level, model.Levels.Count - 1);
            model.VisibleUpTo = level;
            hud.SetLevels(model.Levels.Select(l => Format.LevelLabel(l.Name)).ToList(), level);
            if (!wasPlaced)
            {
                placement.Begin(model);
                return;
            }

            if (viewMode.Mode == ViewMode.Walkthrough)
                ShowWalkthrough();
            else
            {
                viewMode.ShowTabletop(model, animate: false);
                model.RoofVisible = roofVisible;
                model.Exploded = exploded;
                (model.transform.localPosition, model.transform.localRotation, model.transform.localScale) = local;
            }
            RefreshToolbar();
        }

        void OnPlaced()
        {
            viewMode.ShowTabletop(model);
            RefreshToolbar();
            hud.SetHint(PlacedHint);
        }

        void ToggleMode()
        {
            if (viewMode.Mode == ViewMode.Tabletop)
            {
                model.Exploded = false;
                ShowWalkthrough();
            }
            else
            {
                viewMode.ShowTabletop(model);
                model.VisibleUpTo = level;
                hud.SetHint(PlacedHint);
            }
            placement.TapToMove = viewMode.Mode == ViewMode.Tabletop;
            RefreshToolbar();
        }

        void SelectLevel(int index)
        {
            level = index;
            model.VisibleUpTo = index;
            if (viewMode.Mode == ViewMode.Walkthrough)
                ShowWalkthrough();
            RefreshToolbar();
        }

        /// <summary>Stands the viewer in the selected level's largest room. With game controls every level stays up so the stairs lead somewhere.</summary>
        void ShowWalkthrough()
        {
            viewMode.ShowWalkthrough(model, placement.EstimateFloorHeight(), level, firstPerson);
            model.VisibleUpTo = firstPerson ? model.Levels.Count - 1 : level;
            hud.SetHint(WalkthroughHint());
        }

        string WalkthroughHint()
        {
            var building = model.Levels.Count > 1;
            if (firstPerson)
                return building
                    ? "Left thumb to walk, right thumb to look. Take the stairs or pick a level."
                    : "Left thumb to walk, right thumb to look around.";
            return building
                ? $"You're on the {model.Levels[level].Name.ToLowerInvariant()}, in its largest room."
                : "You're standing in the largest room. Walk around to explore.";
        }

        void RefreshToolbar() =>
            hud.ShowPlaced(viewMode.Mode, model.RoofVisible, model.LabelsVisible, model.Exploded, viewMode.FirstPerson);
    }
}
