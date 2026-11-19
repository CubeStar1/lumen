using System;
using System.Collections.Generic;
using FloorPlanViz.Data;
using UnityEngine;

namespace FloorPlanViz.Model
{
    [CreateAssetMenu(menuName = "Floor Plan Viz/Material Palette")]
    public sealed class MaterialPalette : ScriptableObject
    {
        [Serializable]
        public struct FloorMaterial
        {
            public RoomType type;
            public Material material;
        }

        [SerializeField] Material exteriorWall;
        [SerializeField] Material interiorWall;
        [SerializeField] Material wallCap;
        [SerializeField] Material frame;
        [SerializeField] Material glass;
        [SerializeField] Material roof;
        [SerializeField] Material baseBoard;
        [SerializeField] Material shadowCatcher;
        [SerializeField] Material defaultFloor;
        [SerializeField] List<FloorMaterial> floors = new();

        public Material ExteriorWall => exteriorWall;
        public Material InteriorWall => interiorWall;
        public Material WallCap => wallCap;
        public Material Frame => frame;
        public Material Glass => glass;
        public Material Roof => roof;
        public Material BaseBoard => baseBoard;
        public Material ShadowCatcher => shadowCatcher;

        public Material Floor(RoomType type) => Find(type) ?? Find(type.Base()) ?? defaultFloor;

        Material Find(RoomType type)
        {
            foreach (var floor in floors)
            {
                if (floor.type == type)
                    return floor.material;
            }
            return null;
        }
    }
}
