using System.Collections.Generic;
using System.Linq;
using FloorPlanViz.Data;
using FloorPlanViz.Geometry;
using UnityEngine;
using UnityEngine.Rendering;

namespace FloorPlanViz.Model
{
    /// <summary>Turns building geometry into a <see cref="FloorPlanModel"/> hierarchy at 1 unit = 1 metre, one child per level.</summary>
    public sealed class FloorPlanBuilder : MonoBehaviour
    {
        const float LabelLift = 0.5f;
        const float BaseMargin = 0.4f;
        const float BaseThickness = 0.12f;
        const float GroundMargin = 4f;
        const float WalkableMargin = 30f;

        [SerializeField] MaterialPalette palette;
        [SerializeField] RoomLabel labelPrefab;

        public FloorPlanModel Build(BuildingGeometry geometry, Transform parent)
        {
            var root = new GameObject("FloorPlan").transform;
            root.SetParent(parent, false);
            var meshes = new List<Mesh>();
            var levels = geometry.Levels.OrderBy(l => l.Elevation).ToList();

            var levelRoots = levels.Select(level => AddLevel(root, level, meshes)).ToList();

            var top = levels[^1];
            var roof = AddPart(levelRoots[^1], "Roof", PlanMeshBuilder.Roof(top.Rooms.Where(r => !r.Outdoor), top.Height), palette.Roof, meshes);
            var labels = new GameObject("Labels").transform;
            labels.SetParent(root, false);
            var labelGroups = levels.Select(level => AddLabels(labels, level)).ToArray();

            var board = AddPart(root, "Base", PlanMeshBuilder.Base(geometry.Bounds, BaseMargin, BaseThickness), palette.BaseBoard, meshes);
            var ground = AddPart(root, "ShadowCatcher", PlanMeshBuilder.Ground(geometry.Bounds, GroundMargin, -BaseThickness - 0.003f),
                palette.ShadowCatcher, meshes, castShadows: false);
            AddWalkableGround(root, geometry.Bounds);

            var model = root.gameObject.AddComponent<FloorPlanModel>();
            var parts = new ModelParts(roof, levelRoots.ToArray(), labels, labelGroups, new[] { board, ground }, BaseThickness);
            model.Initialize(geometry, parts, meshes);
            model.RoofVisible = false;
            return model;
        }

        Transform AddLevel(Transform root, LevelGeometry level, List<Mesh> meshes)
        {
            var levelRoot = new GameObject(level.Name).transform;
            levelRoot.SetParent(root, false);
            levelRoot.localPosition = Vector3.up * level.Elevation;

            var exterior = PlanMeshBuilder.Walls(level.Walls.Where(w => w.Exterior));
            var interior = PlanMeshBuilder.Walls(level.Walls.Where(w => !w.Exterior));
            AddPart(levelRoot, "ExteriorWalls", exterior.Sides, palette.ExteriorWall, meshes, solid: true);
            AddPart(levelRoot, "InteriorWalls", interior.Sides, palette.InteriorWall, meshes, solid: true);
            AddPart(levelRoot, "ExteriorCaps", exterior.Caps, palette.WallCap, meshes);
            AddPart(levelRoot, "InteriorCaps", interior.Caps, palette.WallCap, meshes);
            AddPart(levelRoot, "Frames", PlanMeshBuilder.Frames(level.Walls), palette.Frame, meshes);
            AddPart(levelRoot, "Glass", PlanMeshBuilder.Glass(level.Walls), palette.Glass, meshes, castShadows: false, solid: true);
            foreach (var rooms in level.Rooms.GroupBy(r => r.Type))
                AddPart(levelRoot, $"Floor_{rooms.Key}", PlanMeshBuilder.Floors(rooms), palette.Floor(rooms.Key), meshes, solid: true);
            AddPart(levelRoot, "Stairs", PlanMeshBuilder.Treads(level.Stairs), palette.Stair, meshes, solid: true);
            AddPart(levelRoot, "Railings", PlanMeshBuilder.Railings(level.Stairs), palette.Railing, meshes, solid: true);
            AddPart(levelRoot, "Columns", PlanMeshBuilder.Columns(level.Columns), palette.Column, meshes, solid: true);
            AddPart(levelRoot, "Slab", PlanMeshBuilder.Slabs(level.Slabs), palette.Slab, meshes, solid: true);
            return levelRoot;
        }

        LabelGroup AddLabels(Transform labels, LevelGeometry level)
        {
            var group = new GameObject(level.Name).transform;
            group.SetParent(labels, false);
            var defaultHeight = level.Height + LabelLift;
            group.localPosition = Vector3.up * (level.Elevation + defaultHeight);
            foreach (var room in level.Rooms)
                Instantiate(labelPrefab, group).Show(room.Name, room.Area, room.Centroid.ToWorld());
            return new LabelGroup(group, level.Elevation, defaultHeight);
        }

        /// <summary>An invisible floor around the building, so a first-person walker can step outside without falling.</summary>
        static void AddWalkableGround(Transform root, PlanBounds bounds)
        {
            var ground = new GameObject("WalkableGround", typeof(BoxCollider));
            ground.transform.SetParent(root, false);
            var size = bounds.Size + Vector2.one * (WalkableMargin * 2f);
            var centre = (bounds.Min.ToVector2() + bounds.Max.ToVector2()) / 2f;
            var box = ground.GetComponent<BoxCollider>();
            box.center = new Vector3(centre.x, -0.5f, centre.y);
            box.size = new Vector3(size.x, 1f, size.y);
        }

        static GameObject AddPart(Transform root, string name, MeshData data, Material material, List<Mesh> meshes, bool castShadows = true,
            bool solid = false)
        {
            var part = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            part.transform.SetParent(root, false);

            var mesh = data.ToMesh(name);
            meshes.Add(mesh);
            part.GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = part.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = castShadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
            if (solid && mesh.vertexCount > 0)
                part.AddComponent<MeshCollider>().sharedMesh = mesh;
            return part;
        }
    }
}
