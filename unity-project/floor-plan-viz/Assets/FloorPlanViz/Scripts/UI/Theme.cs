using UnityEngine;

namespace FloorPlanViz.UI
{
    /// <summary>iOS system colours (light appearance) used across the app.</summary>
    public static class Theme
    {
        public static readonly Color Background = Hex(0xF2F2F7);
        public static readonly Color Surface = Color.white;
        public static readonly Color Label = Hex(0x1C1C1E);
        public static readonly Color SecondaryLabel = Hex(0x8A8A8E);
        public static readonly Color TertiaryLabel = Hex(0xC4C4C6);
        public static readonly Color Separator = Hex(0xE3E3E8);
        public static readonly Color Fill = Hex(0xE9E9EE);
        public static readonly Color Accent = Hex(0x007AFF);
        public static readonly Color AccentTint = new(0f, 0.48f, 1f, 0.12f);
        public static readonly Color Green = Hex(0x34C759);
        public static readonly Color Orange = Hex(0xFF9500);
        public static readonly Color Red = Hex(0xFF3B30);
        public static readonly Color Scrim = new(0f, 0f, 0f, 0.32f);
        public static readonly Color Glass = new(0.08f, 0.08f, 0.1f, 0.55f);
        public static readonly Color GlassActive = new(1f, 1f, 1f, 0.95f);
        public static readonly Color OnGlass = Color.white;

        public static Color Hex(uint rgb) =>
            new(((rgb >> 16) & 0xFF) / 255f, ((rgb >> 8) & 0xFF) / 255f, (rgb & 0xFF) / 255f);

        public static Color WithAlpha(this Color colour, float alpha) => new(colour.r, colour.g, colour.b, alpha);
    }
}
