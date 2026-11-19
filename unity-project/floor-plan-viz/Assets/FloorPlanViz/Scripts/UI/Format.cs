using System;
using System.Globalization;

namespace FloorPlanViz.UI
{
    public static class Format
    {
        public static string Rooms(int count) => count == 1 ? "1 room" : $"{count} rooms";

        public static string Area(float squareMetres) => $"{squareMetres:0.#} m²";

        public static string Size(float width, float depth) => $"{width:0.#} × {depth:0.#} m";

        public static string Summary(int rooms, float area) => $"{Rooms(rooms)} · {Area(area)}";

        public static string Relative(DateTime time)
        {
            var local = time.Kind == DateTimeKind.Unspecified ? time : time.ToLocalTime();
            var age = DateTime.Now - local;
            if (age.TotalMinutes < 1)
                return "Just now";
            if (age.TotalHours < 1)
                return $"{(int)age.TotalMinutes} min ago";
            if (local.Date == DateTime.Today)
                return local.ToString("h:mm tt", CultureInfo.InvariantCulture);
            if (local.Date == DateTime.Today.AddDays(-1))
                return "Yesterday";
            if (age.TotalDays < 7)
                return local.ToString("dddd", CultureInfo.InvariantCulture);
            return local.ToString("d MMM yyyy", CultureInfo.InvariantCulture);
        }
    }
}
