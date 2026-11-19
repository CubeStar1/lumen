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
        public readonly Transform[] Levels;
        public readonly Transform Labels;
        public readonly LabelGroup[] LabelGroups;
        public readonly GameObject[] Base;
        public readonly float BaseThickness;

        public ModelParts(GameObject roof, Transform[] levels, Transform labels, LabelGroup[] labelGroups, GameObject[] baseParts,
            float baseThickness)
        {
            Roof = roof;
            Levels = levels;
            Labels = labels;
            LabelGroups = labelGroups;
            Base = baseParts;
            BaseThickness = baseThickness;
        }
    }

    /// <summary>Root of a built plan. Owns the generated meshes and exposes display toggles.</summary>
    public sealed class FloorPlanModel : MonoBehaviour
    {
        const float ExplodeGap = 0.6f;

        ModelParts parts;
        List<Mesh> meshes;
        float? labelHeight;
        bool exploded;
        int visibleLevels;
        bool roofWanted;

        public BuildingGeometry Geometry { get; private set; }

        /// <summary>The levels from the lowest up; indices below refer to this order.</summary>
        public IReadOnlyList<LevelGeometry> Levels { get; private set; }

        /// <summary>Shows the levels up to and including <paramref name="level"/> and hides those above, like lifting off the upper floors of a dollhouse.</summary>
        public int VisibleUpTo
        {
            get => visibleLevels - 1;
            set
            {
                visibleLevels = Mathf.Clamp(value, 0, Levels.Count - 1) + 1;
                Apply();
            }
        }

        /// <summary>Spreads the levels apart vertically so each one can be seen from the side.</summary>
        public bool Exploded
        {
            get => exploded;
            set
            {
                exploded = value;
                Apply();
            }
        }

        /// <summary>Longest side of the footprint, in metres.</summary>
        public float Footprint => Mathf.Max(Geometry.Bounds.Size.x, Geometry.Bounds.Size.y);

        /// <summary>How far the floor sits above the bottom of the base board, in model units.</summary>
        public float BaseThickness => parts.BaseThickness;

        /// <summary>Centre of the largest indoor room on the ground level, a natural place to stand in walkthrough mode.</summary>
        public Vector3 MainRoomCentre => RoomCentre(0);

        /// <summary>Centre of the largest indoor room on a level, at that level's floor.</summary>
        public Vector3 RoomCentre(int level)
        {
            var target = Levels[Mathf.Clamp(level, 0, Levels.Count - 1)];
            var indoor = target.Rooms.Where(r => !r.Outdoor).ToList();
            var room = (indoor.Count > 0 ? indoor : target.Rooms).OrderByDescending(r => r.Area).First();
            return room.Centroid.ToWorld() + Vector3.up * target.Elevation;
        }

        /// <summary>The roof shows only while every level is visible.</summary>
        public bool RoofVisible
        {
            get => roofWanted;
            set
            {
                roofWanted = value;
                Apply();
            }
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
                labelHeight = value;
                Apply();
            }
        }

        internal void Initialize(BuildingGeometry geometry, ModelParts modelParts, List<Mesh> ownedMeshes)
        {
            Geometry = geometry;
            Levels = geometry.Levels.OrderBy(l => l.Elevation).ToList();
            parts = modelParts;
            meshes = ownedMeshes;
            visibleLevels = Levels.Count;
            Apply();
        }

        void Apply()
        {
            for (var i = 0; i < Levels.Count; i++)
            {
                var lift = exploded ? i * ExplodeGap * Levels[i].Height : 0f;
                var shown = i < visibleLevels;
                parts.Levels[i].localPosition = Vector3.up * (Levels[i].Elevation + lift);
                parts.Levels[i].gameObject.SetActive(shown);
                var group = parts.LabelGroups[i];
                group.Root.localPosition = Vector3.up * (group.Elevation + lift + (labelHeight ?? group.DefaultHeight));
                group.Root.gameObject.SetActive(shown);
            }
            parts.Roof.SetActive(roofWanted && visibleLevels == Levels.Count);
        }

        void OnDestroy()
        {
            foreach (var mesh in meshes)
                Destroy(mesh);
        }
    }
}
