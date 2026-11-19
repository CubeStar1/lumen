namespace FloorPlanViz.Data
{
    /// <summary>Room uses. New values go at the end: materials store these as integers.</summary>
    public enum RoomType
    {
        Living,
        Bedroom,
        Kitchen,
        Bathroom,
        Dining,
        Hallway,
        Balcony,
        Utility,
        Other,
        Toilet,
        Staircase,
        Porch,
        Terrace,
        Store,
        Garage,
    }

    public enum OpeningType
    {
        Door,
        Window,
        SlidingDoor,
        Opening,
    }

    public enum WallKind
    {
        Exterior,
        Interior,
        Partition,
        Low,
        Parapet,
    }

    public enum StairDirection
    {
        Up,
        Down,
    }

    public static class PlanEnumExtensions
    {
        /// <summary>The original room type whose material and style a newer type borrows.</summary>
        public static RoomType Base(this RoomType type) => type switch
        {
            RoomType.Toilet => RoomType.Bathroom,
            RoomType.Staircase => RoomType.Hallway,
            RoomType.Porch or RoomType.Terrace => RoomType.Balcony,
            RoomType.Store or RoomType.Garage => RoomType.Utility,
            _ => type,
        };

        public static bool IsDoor(this OpeningType type) => type is OpeningType.Door or OpeningType.SlidingDoor;
    }
}
