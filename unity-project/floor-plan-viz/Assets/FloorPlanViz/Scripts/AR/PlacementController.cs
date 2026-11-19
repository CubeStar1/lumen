using System;
using System.Collections.Generic;
using FloorPlanViz.Model;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

namespace FloorPlanViz.AR
{
    /// <summary>Places a model on a detected plane, shows a reticle where it will land, and keeps it anchored.</summary>
    public sealed class PlacementController : MonoBehaviour
    {
        static readonly List<ARRaycastHit> Hits = new();

        const float EyeHeight = 1.4f;
        const float MinDropBelowEyes = 0.8f;

        [SerializeField] ARRaycastManager raycastManager;
        [SerializeField] ARPlaneManager planeManager;
        [SerializeField] ARAnchorManager anchorManager;
        [SerializeField] Transform viewer;
        [SerializeField] Transform reticle;

        FloorPlanModel model;
        GameObject anchor;
        bool planesVisible = true;

        public event Action Placed;

        public bool HasSurface => planeManager.trackables.count > 0;
        public bool IsPlaced => model != null && model.gameObject.activeSelf;
        public bool ReticleOnSurface { get; private set; }

        /// <summary>Whether a tap on the camera view moves the placed model.</summary>
        public bool TapToMove { get; set; } = true;

        static Vector2 ScreenCentre => new(Screen.width / 2f, Screen.height / 2f);

        void Awake()
        {
            ScreenInput.Enable();
            planeManager.trackablesChanged.AddListener(OnPlanesChanged);
            reticle.gameObject.SetActive(false);
        }

        void OnDestroy() => planeManager.trackablesChanged.RemoveListener(OnPlanesChanged);

        public void Begin(FloorPlanModel target)
        {
            model = target;
            model.gameObject.SetActive(false);
            TapToMove = true;
            SetPlanesVisible(true);
            enabled = true;
        }

        public bool PlaceAtReticle() => TryPlace(ScreenCentre);

        /// <summary>The real floor: the lowest horizontal plane well below the viewer, or eye height if none is known.</summary>
        public float EstimateFloorHeight()
        {
            var floor = viewer.position.y - EyeHeight;
            var found = false;
            foreach (var plane in planeManager.trackables)
            {
                var height = plane.center.y;
                if (plane.alignment != PlaneAlignment.HorizontalUp || viewer.position.y - height < MinDropBelowEyes)
                    continue;
                floor = found ? Mathf.Min(floor, height) : height;
                found = true;
            }
            return floor;
        }

        public void Clear()
        {
            ReleaseAnchor();
            model = null;
            reticle.gameObject.SetActive(false);
            enabled = false;
        }

        void Update()
        {
            UpdateReticle();
            if (model != null && (TapToMove || !IsPlaced) && ScreenInput.TryGetTap(out var position))
                TryPlace(position);
        }

        void UpdateReticle()
        {
            var hit = default(ARRaycastHit);
            ReticleOnSurface = model != null && !IsPlaced && Raycast(ScreenCentre, out hit);
            reticle.gameObject.SetActive(ReticleOnSurface);
            if (ReticleOnSurface)
                reticle.SetPositionAndRotation(hit.pose.position + Vector3.up * 0.002f, FacingViewer(hit.pose.position));
        }

        bool TryPlace(Vector2 screenPosition)
        {
            if (model == null || !Raycast(screenPosition, out var hit))
                return false;

            var pose = new Pose(hit.pose.position, FacingViewer(hit.pose.position));
            model.transform.SetParent(null, true);
            ReleaseAnchor();
            anchor = CreateAnchor(hit, pose);

            model.transform.SetParent(anchor.transform, false);
            model.transform.localPosition = Vector3.zero;
            model.transform.localRotation = Quaternion.identity;
            model.gameObject.SetActive(true);
            reticle.gameObject.SetActive(false);
            SetPlanesVisible(false);
            Placed?.Invoke();
            return true;
        }

        bool Raycast(Vector2 screenPosition, out ARRaycastHit hit)
        {
            var found = raycastManager.Raycast(screenPosition, Hits, TrackableType.PlaneWithinPolygon);
            hit = found ? Hits[0] : default;
            return found;
        }

        Quaternion FacingViewer(Vector3 position)
        {
            var facing = Vector3.ProjectOnPlane(position - viewer.position, Vector3.up);
            return facing.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(facing) : Quaternion.identity;
        }

        GameObject CreateAnchor(ARRaycastHit hit, Pose pose)
        {
            var plane = planeManager.GetPlane(hit.trackableId);
            var attached = plane != null ? anchorManager.AttachAnchor(plane, pose) : null;
            if (attached != null)
                return attached.gameObject;

            var fallback = new GameObject("Anchor");
            fallback.transform.SetPositionAndRotation(pose.position, pose.rotation);
            return fallback;
        }

        void ReleaseAnchor()
        {
            if (anchor != null)
                Destroy(anchor);
            anchor = null;
        }

        void OnPlanesChanged(ARTrackablesChangedEventArgs<ARPlane> changes)
        {
            foreach (var plane in changes.added)
                plane.gameObject.SetActive(planesVisible);
        }

        void SetPlanesVisible(bool visible)
        {
            planesVisible = visible;
            foreach (var plane in planeManager.trackables)
                plane.gameObject.SetActive(visible);
        }
    }
}
