using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using FloorPlanViz.Geometry;
using UnityEngine;
using UnityEngine.Rendering;

namespace FloorPlanViz.Model
{
    /// <summary>Turns plan geometry into a <see cref="FloorPlanModel"/> hierarchy at 1 unit = 1 metre.</summary>
    public sealed class FloorPlanBuilder : MonoBehaviour
    {
        const float DefaultWallHeight = 3f;
        const float LabelLift = 0.5f;
        const float BaseMargin = 0.4f;
        const float BaseThickness = 0.12f;
        const float GroundMargin = 4f;

        [SerializeField] MaterialPalette palette;
        [SerializeField] RoomLabel labelPrefab;

        public FloorPlanModel Build(PlanGeometry geometry, Transform parent)
        {
            var root = new GameObject("FloorPlan").transform;
            root.SetParent(parent, false);
            var meshes = new List<Mesh>();
            var wallHeight = geometry.Walls.Count > 0 ? geometry.Walls.Max(w => w.Height) : DefaultWallHeight;

            var exterior = PlanMeshBuilder.Walls(geometry.Walls.Where(w => w.Exterior));
            var interior = PlanMeshBuilder.Walls(geometry.Walls.Where(w => !w.Exterior));
            AddPart(root, "ExteriorWalls", exterior.Sides, palette.ExteriorWall, meshes);
            AddPart(root, "InteriorWalls", interior.Sides, palette.InteriorWall, meshes);
            AddPart(root, "ExteriorCaps", exterior.Caps, palette.WallCap, meshes);
            AddPart(root, "InteriorCaps", interior.Caps, palette.WallCap, meshes);
            AddPart(root, "Frames", PlanMeshBuilder.Frames(geometry.Walls), palette.Frame, meshes);
            AddPart(root, "Glass", PlanMeshBuilder.Glass(geometry.Walls), palette.Glass, meshes, castShadows: false);
            foreach (var rooms in geometry.Rooms.GroupBy(r => r.Type))
                AddPart(root, $"Floor_{rooms.Key}", PlanMeshBuilder.Floors(rooms), palette.Floor(rooms.Key), meshes);

            var board = AddPart(root, "Base", PlanMeshBuilder.Base(geometry.Bounds, BaseMargin, BaseThickness), palette.BaseBoard, meshes);
            var ground = AddPart(root, "ShadowCatcher", PlanMeshBuilder.Ground(geometry.Bounds, GroundMargin, -BaseThickness - 0.003f),
                palette.ShadowCatcher, meshes, castShadows: false);
            var roof = AddPart(root, "Roof", PlanMeshBuilder.Roof(geometry.Rooms, wallHeight), palette.Roof, meshes);
            var labels = AddLabels(root, geometry.Rooms, wallHeight + LabelLift);

            var model = root.gameObject.AddComponent<FloorPlanModel>();
            model.Initialize(geometry, new ModelParts(roof, labels, new[] { board, ground }, BaseThickness), meshes);
            model.RoofVisible = false;
            return model;
        }

        Transform AddLabels(Transform root, IEnumerable<RoomData> rooms, float height)
        {
            var labels = new GameObject("Labels").transform;
            labels.SetParent(root, false);
            labels.localPosition = Vector3.up * height;
            foreach (var room in rooms)
                Instantiate(labelPrefab, labels).Show(room.Name, room.Area, room.Centroid.ToWorld());
            return labels;
        }

        static GameObject AddPart(Transform root, string name, MeshData data, Material material, List<Mesh> meshes, bool castShadows = true)
        {
            var part = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            part.transform.SetParent(root, false);

            var mesh = data.ToMesh(name);
            meshes.Add(mesh);
            part.GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = part.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = castShadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
            return part;
        }
    }
}
