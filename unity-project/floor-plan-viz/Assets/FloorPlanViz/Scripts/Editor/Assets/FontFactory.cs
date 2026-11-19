using System.Linq;
using System.Reflection;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;

namespace FloorPlanViz.Editor
{
    /// <summary>Creates the TextMeshPro font assets: Inter with its weights linked, and the icon font.</summary>
    static class FontFactory
    {
        const string Common = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~·×²–—…’‘“”•°";

        public static TMP_FontAsset Text()
        {
            var regular = Create("Inter-Regular", 90, 1024);
            var table = regular.fontWeightTable;
            table[5].regularTypeface = Create("Inter-Medium", 90, 1024);
            table[6].regularTypeface = Create("Inter-SemiBold", 90, 1024);
            table[7].regularTypeface = Create("Inter-Bold", 90, 1024);
            EditorUtility.SetDirty(regular);
            return regular;
        }

        public static TMP_FontAsset Icons()
        {
            var glyphs = typeof(UI.Icons).GetFields(BindingFlags.Public | BindingFlags.Static)
                .Select(f => (string)f.GetRawConstantValue());
            return Create("MaterialIconsRound-Regular", 64, 512, string.Concat(glyphs), extension: "otf");
        }

        static TMP_FontAsset Create(string fontName, int samplingSize, int atlasSize, string characters = Common, string extension = "ttf")
        {
            var path = $"{ProjectPaths.Fonts}/{fontName} SDF.asset";
            var existing = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(path);
            if (existing != null)
                return existing;

            var font = AssetDatabase.LoadAssetAtPath<Font>($"{ProjectPaths.Fonts}/{fontName}.{extension}");
            var asset = TMP_FontAsset.CreateFontAsset(font, samplingSize, samplingSize / 10, GlyphRenderMode.SDFAA,
                atlasSize, atlasSize, AtlasPopulationMode.Dynamic, enableMultiAtlasSupport: true);
            asset.name = $"{fontName} SDF";
            AssetDatabase.CreateAsset(asset, path);

            asset.TryAddCharacters(characters, out _);
            foreach (var texture in asset.atlasTextures)
            {
                texture.name = $"{fontName} Atlas";
                if (!AssetDatabase.IsSubAsset(texture))
                    AssetDatabase.AddObjectToAsset(texture, asset);
            }
            asset.material.name = $"{fontName} Material";
            if (!AssetDatabase.IsSubAsset(asset.material))
                AssetDatabase.AddObjectToAsset(asset.material, asset);

            EditorUtility.SetDirty(asset);
            AssetDatabase.SaveAssets();
            return asset;
        }
    }
}
