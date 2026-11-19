using UnityEngine;

namespace FloorPlanViz.Editor
{
    /// <summary>Pixel functions for the generated textures. All surface patterns tile seamlessly.</summary>
    static class Procedural
    {
        public static float Hash(int a, int b)
        {
            unchecked
            {
                var h = (uint)(a * 374761393 + b * 668265263);
                h = (h ^ (h >> 13)) * 1274126177u;
                return (h ^ (h >> 16)) / (float)uint.MaxValue;
            }
        }

        /// <summary>Tileable Perlin noise for u, v in [0, 1), stretched by separate frequencies.</summary>
        public static float Noise(float u, float v, float frequencyU, float frequencyV, int seed)
        {
            var offset = 50f + seed * 13.37f;
            float Sample(float x, float y) => Mathf.PerlinNoise(x * frequencyU + offset, y * frequencyV + offset * 0.71f);
            var top = Mathf.Lerp(Sample(u, v), Sample(u - 1f, v), u);
            var bottom = Mathf.Lerp(Sample(u, v - 1f), Sample(u - 1f, v - 1f), u);
            return Mathf.Lerp(top, bottom, v);
        }

        /// <summary>Planks running along u, <paramref name="rows"/> per tile, each row's joint at a random point.</summary>
        public static Color Planks(int x, int y, int size, int rows, Color light, Color dark, float gapPixels, int seed)
        {
            var u = (x + 0.5f) / size;
            var v = (y + 0.5f) / size;
            var rowSize = (float)size / rows;
            var row = Mathf.FloorToInt(y / rowSize);
            var along = Mathf.Repeat(u - Hash(row, seed), 1f);

            var tone = Hash(row, seed + 11);
            var grain = Noise(u, v, 3f, 90f, seed) * 0.55f + Noise(u, v, 18f, 260f, seed + 5) * 0.45f;
            var knots = Mathf.Pow(Noise(u, v, 9f, 30f, seed + 9), 6f);
            var colour = Color.Lerp(light, dark, Mathf.Clamp01(0.15f + tone * 0.5f + (grain - 0.5f) * 0.7f + knots * 0.6f));

            var rowEdge = Mathf.Min(y - row * rowSize, (row + 1) * rowSize - y);
            var jointEdge = Mathf.Min(along, 1f - along) * size;
            var seam = Mathf.Clamp01((Mathf.Min(rowEdge, jointEdge) - gapPixels * 0.5f) / 1.2f);
            return Color.Lerp(dark * 0.55f, colour, seam).WithOpaque();
        }

        public static Color Tiles(int x, int y, int size, int count, Color tile, Color grout, float groutPixels, float variation, int seed)
        {
            var cell = (float)size / count;
            var cx = Mathf.FloorToInt(x / cell);
            var cy = Mathf.FloorToInt(y / cell);
            var lx = x - cx * cell;
            var ly = y - cy * cell;
            var edge = Mathf.Min(Mathf.Min(lx, cell - lx), Mathf.Min(ly, cell - ly));

            var u = (x + 0.5f) / size;
            var v = (y + 0.5f) / size;
            var tone = (Hash(cx + cy * 97, seed) - 0.5f) * variation;
            var mottle = (Noise(u, v, 12f, 12f, seed) - 0.5f) * variation * 0.8f;
            var surface = tile * (1f + tone + mottle);
            var bevel = Mathf.Lerp(0.93f, 1f, Mathf.Clamp01((edge - groutPixels / 2f) / 3f));
            var mix = Mathf.Clamp01((edge - groutPixels / 2f) / 1.2f);
            return Color.Lerp(grout, surface * bevel, mix).WithOpaque();
        }

        public static Color Speckled(int x, int y, int size, Color colour, float coarse, float fine, int seed)
        {
            var u = (x + 0.5f) / size;
            var v = (y + 0.5f) / size;
            var amount = (Noise(u, v, 4f, 4f, seed) - 0.5f) * coarse + (Noise(u, v, 48f, 48f, seed + 3) - 0.5f) * fine;
            return (colour * (1f + amount)).WithOpaque();
        }

        /// <summary>A white rounded square with anti-aliased corners, for 9-slicing.</summary>
        public static Color Rounded(int x, int y, int size, float radius)
        {
            var px = Mathf.Min(x + 0.5f, size - x - 0.5f);
            var py = Mathf.Min(y + 0.5f, size - y - 0.5f);
            var dx = Mathf.Max(radius - px, 0f);
            var dy = Mathf.Max(radius - py, 0f);
            var outside = Mathf.Sqrt(dx * dx + dy * dy) - radius;
            return White(Mathf.Clamp01(0.5f - outside));
        }

        /// <summary>A soft blurred rounded rectangle, for drop shadows.</summary>
        public static Color Shadow(int x, int y, int size, float inset, float radius, float blur)
        {
            var px = Mathf.Min(x + 0.5f, size - x - 0.5f) - inset;
            var py = Mathf.Min(y + 0.5f, size - y - 0.5f) - inset;
            var dx = Mathf.Max(radius - px, 0f);
            var dy = Mathf.Max(radius - py, 0f);
            var outside = Mathf.Max(Mathf.Sqrt(dx * dx + dy * dy) - radius, 0f);
            var falloff = 1f - Mathf.SmoothStep(0f, 1f, outside / blur);
            return new Color(0f, 0f, 0f, falloff * falloff);
        }

        /// <summary>A ring whose opacity fades around the circle, for the activity spinner.</summary>
        public static Color SpinnerRing(int x, int y, int size, float stroke)
        {
            var (distance, angle) = Polar(x, y, size);
            var radius = size / 2f - stroke / 2f - 1f;
            var ring = Mathf.Clamp01(stroke / 2f + 0.5f - Mathf.Abs(distance - radius));
            var sweep = Mathf.Repeat(angle / (2f * Mathf.PI), 1f);
            return White(ring * Mathf.Lerp(0.1f, 1f, sweep * sweep));
        }

        /// <summary>The AR placement target: a ring with a faint fill and a centre dot.</summary>
        public static Color Reticle(int x, int y, int size)
        {
            var (distance, _) = Polar(x, y, size);
            var r = distance / (size / 2f);
            var pixel = 2f / size;
            var ring = Mathf.Clamp01(1f - Mathf.Abs(r - 0.9f) / 0.045f - pixel);
            var dot = Mathf.Clamp01((0.06f - r) / pixel);
            var fill = r < 0.9f ? 0.14f : 0f;
            return White(Mathf.Max(Mathf.Max(ring, dot), fill));
        }

        public static Color Dot(int x, int y, int size, float radius)
        {
            var (distance, _) = Polar(x, y, size);
            return White(Mathf.Clamp01(radius + 0.5f - distance) * 0.85f);
        }

        static (float distance, float angle) Polar(int x, int y, int size)
        {
            var dx = x + 0.5f - size / 2f;
            var dy = y + 0.5f - size / 2f;
            return (Mathf.Sqrt(dx * dx + dy * dy), Mathf.Atan2(dy, dx));
        }

        static Color White(float alpha) => new(1f, 1f, 1f, alpha);

        static Color WithOpaque(this Color colour) => new(colour.r, colour.g, colour.b, 1f);
    }
}
