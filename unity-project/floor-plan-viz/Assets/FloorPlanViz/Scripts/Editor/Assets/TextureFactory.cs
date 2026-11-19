using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace FloorPlanViz.Editor
{
    /// <summary>Renders pixel functions to PNG assets and imports them as tiling surfaces or UI sprites.</summary>
    static class TextureFactory
    {
        public static Texture2D Surface(string name, int size, Func<int, int, int, Color> pixel) =>
            Write($"{ProjectPaths.Textures}/{name}.png", size, pixel, importer =>
            {
                importer.textureType = TextureImporterType.Default;
                importer.wrapMode = TextureWrapMode.Repeat;
                importer.mipmapEnabled = true;
                importer.anisoLevel = 8;
                importer.filterMode = FilterMode.Trilinear;
            }, AssetDatabase.LoadAssetAtPath<Texture2D>);

        public static Texture2D Mask(string name, int size, Func<int, int, int, Color> pixel, bool repeat = false) =>
            Write($"{ProjectPaths.Textures}/{name}.png", size, pixel, importer =>
            {
                importer.textureType = TextureImporterType.Default;
                importer.alphaIsTransparency = true;
                importer.wrapMode = repeat ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
                importer.mipmapEnabled = true;
                importer.anisoLevel = 4;
            }, AssetDatabase.LoadAssetAtPath<Texture2D>);

        public static Sprite Sprite(string name, int size, Func<int, int, int, Color> pixel, float border = 0f, float pixelsPerUnit = 100f) =>
            Write($"{ProjectPaths.Sprites}/{name}.png", size, pixel, importer =>
            {
                importer.textureType = TextureImporterType.Sprite;
                importer.spriteImportMode = SpriteImportMode.Single;
                importer.spritePixelsPerUnit = pixelsPerUnit;
                importer.spriteBorder = Vector4.one * border;
                var settings = new TextureImporterSettings();
                importer.ReadTextureSettings(settings);
                settings.spriteMeshType = SpriteMeshType.FullRect;
                importer.SetTextureSettings(settings);
                importer.alphaIsTransparency = true;
                importer.mipmapEnabled = false;
                importer.wrapMode = TextureWrapMode.Clamp;
                importer.textureCompression = TextureImporterCompression.Uncompressed;
            }, AssetDatabase.LoadAssetAtPath<Sprite>);

        static T Write<T>(string path, int size, Func<int, int, int, Color> pixel, Action<TextureImporter> configure,
            Func<string, T> load) where T : UnityEngine.Object
        {
            var pixels = new Color[size * size];
            for (var y = 0; y < size; y++)
            for (var x = 0; x < size; x++)
                pixels[y * size + x] = pixel(x, y, size);

            var texture = new Texture2D(size, size, TextureFormat.RGBA32, false);
            texture.SetPixels(pixels);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllBytes(path, texture.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(texture);

            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            configure(importer);
            importer.SaveAndReimport();
            return load(path);
        }
    }
}
