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
            var geometry = LoadSample().Geometry;
            var level = geometry.Ground;

            Assert.AreEqual(1, geometry.Levels.Count);
            Assert.AreEqual(7, level.Rooms.Count);
            Assert.AreEqual(RoomType.Living, level.Rooms[0].Type);
            Assert.AreEqual(3f, level.Height);
            Assert.IsTrue(level.Walls.All(w => w.Kind is WallKind.Exterior or WallKind.Interior));
            Assert.IsTrue(level.Walls.SelectMany(w => w.Openings).Any(o => o.Type == OpeningType.Window));
        }

        [Test]
        public void SpecRoundTripsUnchanged()
        {
            var json = PlanJson.Serialize(LoadSample().Spec);

            StringAssert.Contains("\"kind\":\"floor\"", json);
            StringAssert.Contains("\"outdoor\":false", json);
            StringAssert.Contains("\"type\":\"living\"", json);
        }

        [Test]
        public void NewEnumValuesParseFromSnakeCase()
        {
            var opening = PlanJson.Deserialize<OpeningData>("{\"type\":\"sliding_door\"}");
            var room = PlanJson.Deserialize<RoomData>("{\"type\":\"porch\",\"outdoor\":true}");

            Assert.AreEqual(OpeningType.SlidingDoor, opening.Type);
            Assert.AreEqual(RoomType.Porch, room.Type);
            Assert.AreEqual(RoomType.Balcony, room.Type.Base());
            Assert.IsTrue(room.Outdoor);
        }

        [Test]
        public void NotesComeFromTheSpec()
        {
            var notes = PlanJson.Notes(LoadSample()).ToList();

            Assert.AreEqual(1, notes.Count);
            StringAssert.Contains("Hand-written sample", notes[0]);
        }

        [Test]
        public void SampleBuildsNonEmptyMeshes()
        {
            var level = LoadSample().Geometry.Ground;

            var walls = PlanMeshBuilder.Walls(level.Walls);
            Assert.Greater(walls.Sides.TriangleCount, 0);
            Assert.Greater(walls.Caps.TriangleCount, 0);
            Assert.Greater(PlanMeshBuilder.Floors(level.Rooms).TriangleCount, 0);
            Assert.Greater(PlanMeshBuilder.Glass(level.Walls).TriangleCount, 0);
            Assert.Greater(PlanMeshBuilder.Frames(level.Walls).TriangleCount, 0);
        }
    }
}
