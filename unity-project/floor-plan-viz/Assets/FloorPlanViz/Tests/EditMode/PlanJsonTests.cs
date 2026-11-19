using System.Linq;
using FloorPlanViz.Api;
using FloorPlanViz.Data;
using FloorPlanViz.Geometry;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace FloorPlanViz.Tests
{
    public sealed class PlanJsonTests
    {
        const string SamplePath = "Assets/FloorPlanViz/Samples/two_bedroom.json";

        static PlanResponse LoadSample() =>
            PlanJson.Deserialize<PlanResponse>(AssetDatabase.LoadAssetAtPath<TextAsset>(SamplePath).text);

        [Test]
        public void SampleResponseDeserializes()
        {
            var response = LoadSample();

            Assert.AreEqual(7, response.Geometry.Rooms.Count);
            Assert.AreEqual(RoomType.Living, response.Geometry.Rooms[0].Type);
            Assert.AreEqual(3f, response.Spec.WallHeight);
            Assert.IsTrue(response.Geometry.Walls.SelectMany(w => w.Openings).Any(o => o.Type == OpeningType.Window));
        }

        [Test]
        public void SpecSerializesInSnakeCase()
        {
            var json = PlanJson.Serialize(LoadSample().Spec);

            StringAssert.Contains("\"wall_height\":3.0", json);
            StringAssert.Contains("\"type\":\"living\"", json);
        }

        [Test]
        public void SampleBuildsNonEmptyMeshes()
        {
            var geometry = LoadSample().Geometry;

            var walls = PlanMeshBuilder.Walls(geometry.Walls);
            Assert.Greater(walls.Sides.TriangleCount, 0);
            Assert.Greater(walls.Caps.TriangleCount, 0);
            Assert.Greater(PlanMeshBuilder.Floors(geometry.Rooms).TriangleCount, 0);
            Assert.Greater(PlanMeshBuilder.Glass(geometry.Walls).TriangleCount, 0);
            Assert.Greater(PlanMeshBuilder.Frames(geometry.Walls).TriangleCount, 0);
        }
    }
}
