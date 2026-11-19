using System;
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

        public event Action CloseRequested;
        public event Action EditRequested;

        public bool IsActive => model != null;

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
            placement.Begin(model);
            hud.ShowPlacing(document.Name);
        }

        public void Exit()
        {
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
            var local = (model.transform.localPosition, model.transform.localRotation, model.transform.localScale);
            Destroy(model.gameObject);

            model = builder.Build(plan.Geometry, parent);
            model.LabelsVisible = labelsVisible;
            if (!wasPlaced)
            {
                placement.Begin(model);
                return;
            }

            if (viewMode.Mode == ViewMode.Walkthrough)
                viewMode.ShowWalkthrough(model, placement.EstimateFloorHeight());
            else
            {
                viewMode.ShowTabletop(model, animate: false);
                model.RoofVisible = roofVisible;
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
                viewMode.ShowWalkthrough(model, placement.EstimateFloorHeight());
                hud.SetHint("You're standing in the largest room. Walk around to explore.");
            }
            else
            {
                viewMode.ShowTabletop(model);
                hud.SetHint(PlacedHint);
            }
            placement.TapToMove = viewMode.Mode == ViewMode.Tabletop;
            RefreshToolbar();
        }

        void RefreshToolbar() => hud.ShowPlaced(viewMode.Mode, model.RoofVisible, model.LabelsVisible);
    }
}
