using FloorPlanViz.Data;
using UnityEngine;

namespace FloorPlanViz.UI
{
    /// <summary>How each room type is shown in 2D: fill colour, display name and icon.</summary>
    public static class RoomStyle
    {
        public static Color Colour(RoomType type) => type switch
        {
            RoomType.Living => Theme.Hex(0xF6D3A5),
            RoomType.Bedroom => Theme.Hex(0xBCD2F7),
            RoomType.Kitchen => Theme.Hex(0xF8BFB3),
            RoomType.Bathroom => Theme.Hex(0xB5E4EC),
            RoomType.Dining => Theme.Hex(0xF6E3A6),
            RoomType.Hallway => Theme.Hex(0xE2E2E7),
            RoomType.Balcony => Theme.Hex(0xBFE6C4),
            RoomType.Utility => Theme.Hex(0xD9CCF0),
            _ => Theme.Hex(0xE6E6EB),
        };

        public static string Name(RoomType type) => type switch
        {
            RoomType.Living => "Living",
            RoomType.Bedroom => "Bedroom",
            RoomType.Kitchen => "Kitchen",
            RoomType.Bathroom => "Bathroom",
            RoomType.Dining => "Dining",
            RoomType.Hallway => "Hallway",
            RoomType.Balcony => "Balcony",
            RoomType.Utility => "Utility",
            _ => "Other",
        };

        public static string Icon(RoomType type) => type switch
        {
            RoomType.Living => Icons.Weekend,
            RoomType.Bedroom => Icons.Bed,
            RoomType.Kitchen => Icons.Kitchen,
            RoomType.Bathroom => Icons.Bathtub,
            RoomType.Dining => Icons.Dining,
            RoomType.Hallway => Icons.DoorFront,
            RoomType.Balcony => Icons.Deck,
            RoomType.Utility => Icons.Laundry,
            _ => Icons.Category,
        };
    }
}
