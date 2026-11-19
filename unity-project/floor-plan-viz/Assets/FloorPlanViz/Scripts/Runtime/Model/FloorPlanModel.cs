using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using UnityEngine;

namespace FloorPlanViz.Model
{
    /// <summary>The room labels of one level, at its elevation plus a height that walkthrough mode can lower.</summary>
    public readonly struct LabelGroup
    {
        public readonly Transform Root;
        public readonly float Elevation;
        public readonly float DefaultHeight;

        public LabelGroup(Transform root, float elevation, float defaultHeight)
        {
            Root = root;
            Elevation = elevation;
            DefaultHeight = defaultHeight;
        }
    }

    public readonly struct ModelParts
    {
        public readonly GameObject Roof;
        public readonly Transform Labels;
        public readonly LabelGroup[] LabelGroups;
        public readonly GameObject[] Base;
        public readonly float BaseThickness;

        public ModelParts(GameObject roof, Transform labels, LabelGroup[] labelGroups, GameObject[] baseParts, float baseThickness)
        {
            Roof = roof;
            Labels = labels;
            LabelGroups = labelGroups;
            Base = baseParts;
            BaseThickness = baseThickness;
        }
    }

    /// <summary>Root of a built plan. Owns the generated meshes and exposes display toggles.</summary>
    public sealed class FloorPlanModel : MonoBehaviour
    {
        ModelParts parts;
        List<Mesh> meshes;

        public BuildingGeometry Geometry { get; private set; }

        /// <summary>Longest side of the footprint, in metres.</summary>
        public float Footprint => Mathf.Max(Geometry.Bounds.Size.x, Geometry.Bounds.Size.y);

        /// <summary>How far the floor sits above the bottom of the base board, in model units.</summary>
        public float BaseThickness => parts.BaseThickness;

        /// <summary>Centre of the largest indoor room on the ground level, a natural place to stand in walkthrough mode.</summary>
        public Vector3 MainRoomCentre
        {
            get
            {
                var ground = Geometry.Ground;
                var indoor = ground.Rooms.Where(r => !r.Outdoor).ToList();
                var room = (indoor.Count > 0 ? indoor : ground.Rooms).OrderByDescending(r => r.Area).First();
                return room.Centroid.ToWorld() + Vector3.up * ground.Elevation;
            }
        }

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

        /// <summary>Height of the room labels above each level's floor; null puts them back above the walls.</summary>
        public float? LabelHeight
        {
            set
            {
                foreach (var group in parts.LabelGroups)
                    group.Root.localPosition = Vector3.up * (group.Elevation + (value ?? group.DefaultHeight));
            }
        }

        internal void Initialize(BuildingGeometry geometry, ModelParts modelParts, List<Mesh> ownedMeshes)
        {
            Geometry = geometry;
            parts = modelParts;
            meshes = ownedMeshes;
        }

        void OnDestroy()
        {
            foreach (var mesh in meshes)
                Destroy(mesh);
        }
    }
}
