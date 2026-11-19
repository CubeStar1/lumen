using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using UnityEngine;

namespace FloorPlanViz.Model
{
    public readonly struct ModelParts
    {
        public readonly GameObject Roof;
        public readonly Transform Labels;
        public readonly GameObject[] Base;
        public readonly float BaseThickness;

        public ModelParts(GameObject roof, Transform labels, GameObject[] baseParts, float baseThickness)
        {
            Roof = roof;
            Labels = labels;
            Base = baseParts;
            BaseThickness = baseThickness;
        }
    }

    /// <summary>Root of a built plan. Owns the generated meshes and exposes display toggles.</summary>
    public sealed class FloorPlanModel : MonoBehaviour
    {
        ModelParts parts;
        List<Mesh> meshes;
        float defaultLabelHeight;

        public PlanGeometry Geometry { get; private set; }

        /// <summary>Longest side of the footprint, in metres.</summary>
        public float Footprint => Mathf.Max(Geometry.Bounds.Size.x, Geometry.Bounds.Size.y);

        /// <summary>How far the floor sits above the bottom of the base board, in model units.</summary>
        public float BaseThickness => parts.BaseThickness;

        /// <summary>Centre of the largest room in plan space, a natural place to stand in walkthrough mode.</summary>
        public Vector3 MainRoomCentre => Geometry.Rooms.OrderByDescending(r => r.Area).First().Centroid.ToWorld();

        public bool RoofVisible
        {
            get => parts.Roof.activeSelf;
            set => parts.Roof.SetActive(value);
        }

        public bool LabelsVisible
        {
            get => parts.Labels.gameObject.activeSelf;
            set => parts.Labels.gameObject.SetActive(value);
        }

        public bool BaseVisible
        {
            set
            {
                foreach (var part in parts.Base)
                    part.SetActive(value);
            }
        }

        /// <summary>Height of the room labels above the floor; null puts them back above the walls.</summary>
        public float? LabelHeight
        {
            set => parts.Labels.localPosition = Vector3.up * (value ?? defaultLabelHeight);
        }

        internal void Initialize(PlanGeometry geometry, ModelParts modelParts, List<Mesh> ownedMeshes)
        {
            Geometry = geometry;
            parts = modelParts;
            meshes = ownedMeshes;
            defaultLabelHeight = parts.Labels.localPosition.y;
        }

        void OnDestroy()
        {
            foreach (var mesh in meshes)
                Destroy(mesh);
        }
    }
}
