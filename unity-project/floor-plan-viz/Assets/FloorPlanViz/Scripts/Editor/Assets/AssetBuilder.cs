using FloorPlanViz.Api;
using FloorPlanViz.Data;
using FloorPlanViz.Model;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using static FloorPlanViz.Editor.Procedural;

namespace FloorPlanViz.Editor
{
    /// <summary>The generated sprites and fonts the UI is built from.</summary>
    sealed class UiAssets
    {
        public const float RoundedBorder = 48f;

        public Sprite Rounded;
        public Sprite Shadow;
        public Sprite Spinner;
        public TMP_FontAsset Font;
        public TMP_FontAsset IconFont;
    }

    /// <summary>Creates or updates the project's generated assets. Safe to run repeatedly.</summary>
    public static class AssetBuilder
    {
        const int SurfaceSize = 1024;
        const float PlankTile = 1.2f;

        [MenuItem("Floor Plan Viz/Build Assets")]
        public static void BuildAll()
        {
            Palette();
            LabelPrefab();
            PlanePrefab();
            ReticlePrefab();
            ApiSettings();
            AssetDatabase.SaveAssets();
        }

        internal static UiAssets Ui() => new()
        {
            Rounded = LoadOr("Rounded", () => TextureFactory.Sprite("Rounded", 128, (x, y, s) => Rounded(x, y, s, UiAssets.RoundedBorder), UiAssets.RoundedBorder)),
            Shadow = LoadOr("Shadow", () => TextureFactory.Sprite("Shadow", 128, (x, y, s) => Shadow(x, y, s, 40f, 16f, 36f), 60f)),
            Spinner = LoadOr("Spinner", () => TextureFactory.Sprite("Spinner", 128, (x, y, s) => SpinnerRing(x, y, s, 12f))),
            Font = FontFactory.Text(),
            IconFont = FontFactory.Icons(),
        };

        public static MaterialPalette Palette()
        {
            var palette = LoadOrCreate<MaterialPalette>($"{ProjectPaths.Settings}/MaterialPalette.asset");
            var plaster = Surface("Plaster", 512, (x, y, s) => Speckled(x, y, s, Color.white, 0.05f, 0.04f, 1));
            var concrete = Surface("Concrete", 512, (x, y, s) => Speckled(x, y, s, Color.white, 0.14f, 0.1f, 2));

            SerializedWiring.Set(palette, "exteriorWall", MaterialFactory.Lit("ExteriorWall", Theme(0xEEEAE3), 0.12f, plaster, 2f));
            SerializedWiring.Set(palette, "interiorWall", MaterialFactory.Lit("InteriorWall", Theme(0xF7F6F3), 0.12f, plaster, 2f));
            SerializedWiring.Set(palette, "wallCap", MaterialFactory.Lit("WallCap", Theme(0x2E2F33), 0.2f));
            SerializedWiring.Set(palette, "frame", MaterialFactory.Lit("Frame", Theme(0x3A3B40), 0.55f, metallic: 0.4f));
            SerializedWiring.Set(palette, "glass", MaterialFactory.Glass("Glass", new Color(0.62f, 0.8f, 0.92f, 0.32f), 0.95f));
            SerializedWiring.Set(palette, "roof", MaterialFactory.Lit("Roof", Theme(0xD6D2CB), 0.1f, concrete, 2f));
            SerializedWiring.Set(palette, "baseBoard", MaterialFactory.Lit("BaseBoard", Theme(0xFAF9F7), 0.25f));
            SerializedWiring.Set(palette, "stair", MaterialFactory.Lit("Stair", Theme(0xE4DED4), 0.2f, concrete, 2f));
            SerializedWiring.Set(palette, "railing", MaterialFactory.Lit("Railing", Theme(0x2E2F33), 0.6f, metallic: 0.5f));
            SerializedWiring.Set(palette, "slab", MaterialFactory.Lit("Slab", Theme(0xCFCAC2), 0.1f, concrete, 2f));
            SerializedWiring.Set(palette, "column", MaterialFactory.Lit("Column", Theme(0xE8E4DD), 0.12f, plaster, 2f));
            SerializedWiring.Set(palette, "shadowCatcher", MaterialFactory.ShadowCatcher("ShadowCatcher", 0.38f));
            SerializedWiring.Set(palette, "defaultFloor", MaterialFactory.Lit("Floor_Other", Theme(0xD8D7D2), 0.2f, concrete, 2f));

            var floors = new (RoomType type, Material material)[]
            {
                (RoomType.Living, Wood("Floor_Living", "Oak", Theme(0xD2AB80), Theme(0x8C643E))),
                (RoomType.Dining, Wood("Floor_Dining", "Oak", Theme(0xD2AB80), Theme(0x8C643E))),
                (RoomType.Bedroom, Wood("Floor_Bedroom", "Ash", Theme(0xE2CCAA), Theme(0xAE8F69))),
                (RoomType.Hallway, Tile("Floor_Hallway", "StoneTiles", 2, Theme(0xE6E2DB), Theme(0xBDB7AE), 0.05f, 0.35f)),
                (RoomType.Kitchen, Tile("Floor_Kitchen", "KitchenTiles", 4, Theme(0xDDD6CB), Theme(0xA9A196), 0.06f, 0.45f)),
                (RoomType.Bathroom, Tile("Floor_Bathroom", "BathTiles", 8, Theme(0xDDEBF0), Theme(0xAFC0C7), 0.04f, 0.6f)),
                (RoomType.Balcony, Deck()),
                (RoomType.Utility, MaterialFactory.Lit("Floor_Utility", Theme(0xBDBDB9), 0.25f, concrete, 2f)),
            };

            var serialized = new SerializedObject(palette);
            var entries = serialized.FindProperty("floors");
            entries.arraySize = floors.Length;
            for (var i = 0; i < floors.Length; i++)
            {
                var entry = entries.GetArrayElementAtIndex(i);
                entry.FindPropertyRelative("type").enumValueIndex = (int)floors[i].type;
                entry.FindPropertyRelative("material").objectReferenceValue = floors[i].material;
            }
            serialized.ApplyModifiedPropertiesWithoutUndo();
            return palette;
        }

        static Material Wood(string name, string texture, Color light, Color dark)
        {
            var map = Surface(texture, SurfaceSize, (x, y, s) => Planks(x, y, s, 8, light, dark, 1.5f, texture.Length));
            return MaterialFactory.Lit(name, Color.white, 0.38f, map, PlankTile);
        }

        static Material Tile(string name, string texture, int perTile, Color tile, Color grout, float variation, float smoothness)
        {
            var map = Surface(texture, SurfaceSize, (x, y, s) => Tiles(x, y, s, perTile, tile, grout, 4f, variation, perTile));
            return MaterialFactory.Lit(name, Color.white, smoothness, map, PlankTile);
        }

        static Material Deck()
        {
            var map = Surface("Deck", SurfaceSize, (x, y, s) => Planks(x, y, s, 7, Theme(0xA48E78), Theme(0x5F4F42), 6f, 3));
            return MaterialFactory.Lit("Floor_Balcony", Color.white, 0.2f, map, PlankTile);
        }

        public static RoomLabel LabelPrefab()
        {
            var path = $"{ProjectPaths.Prefabs}/RoomLabel.prefab";
            if (AssetDatabase.LoadAssetAtPath<RoomLabel>(path) == null)
                SaveAsPrefab(new GameObject("RoomLabel", typeof(TextMeshPro), typeof(RoomLabel)), path);

            var font = FontFactory.Text();
            var pill = LoadOr("LabelPill", () => TextureFactory.Sprite("LabelPill", 128, (x, y, s) => Rounded(x, y, s, UiAssets.RoundedBorder), UiAssets.RoundedBorder, 320f));
            using (var prefab = new PrefabUtility.EditPrefabContentsScope(path))
            {
                var root = prefab.prefabContentsRoot;
                var text = root.GetComponent<TextMeshPro>();
                text.font = font;
                text.fontSharedMaterial = font.material;
                text.text = "Room";
                text.fontSize = 2.4f;
                text.fontWeight = FontWeight.SemiBold;
                text.alignment = TextAlignmentOptions.Center;
                text.textWrappingMode = TextWrappingModes.NoWrap;
                text.color = UI.Theme.Label;
                text.rectTransform.sizeDelta = new Vector2(4f, 1f);
                text.sortingOrder = 1;
                var textRenderer = root.GetComponent<MeshRenderer>();
                textRenderer.shadowCastingMode = ShadowCastingMode.Off;
                textRenderer.receiveShadows = false;

                var background = root.GetComponentInChildren<SpriteRenderer>() ?? AddLabelBackground(root.transform);
                background.sprite = pill;
                background.drawMode = SpriteDrawMode.Sliced;
                background.color = new Color(1f, 1f, 1f, 0.92f);
                background.sortingOrder = 0;
                background.shadowCastingMode = ShadowCastingMode.Off;
                SerializedWiring.Set(root.GetComponent<RoomLabel>(), "background", background);
            }
            return AssetDatabase.LoadAssetAtPath<RoomLabel>(path);
        }

        static SpriteRenderer AddLabelBackground(Transform label)
        {
            var background = new GameObject("Background", typeof(SpriteRenderer));
            background.transform.SetParent(label, false);
            return background.GetComponent<SpriteRenderer>();
        }

        public static GameObject PlanePrefab()
        {
            var path = $"{ProjectPaths.Prefabs}/ARPlane.prefab";
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
            {
                EditorApplication.ExecuteMenuItem("GameObject/XR/AR Default Plane");
                SaveAsPrefab(Selection.activeGameObject, path);
            }

            var dots = TextureFactory.Mask("PlaneDots", 64, (x, y, s) => Dot(x, y, s, 3.2f), repeat: true);
            using (var prefab = new PrefabUtility.EditPrefabContentsScope(path))
            {
                var root = prefab.prefabContentsRoot;
                var surface = root.GetComponent<MeshRenderer>();
                surface.sharedMaterial = MaterialFactory.Unlit("PlaneDots", new Color(1f, 1f, 1f, 0.75f), dots, 12f);
                surface.shadowCastingMode = ShadowCastingMode.Off;
                var outline = root.GetComponent<LineRenderer>();
                outline.sharedMaterial = MaterialFactory.Unlit("PlaneOutline", new Color(1f, 1f, 1f, 0.6f), null);
                outline.startWidth = outline.endWidth = 0.004f;
                outline.startColor = outline.endColor = Color.white;
            }
            return AssetDatabase.LoadAssetAtPath<GameObject>(path);
        }

        public static GameObject ReticlePrefab()
        {
            var path = $"{ProjectPaths.Prefabs}/Reticle.prefab";
            var texture = TextureFactory.Mask("Reticle", 256, Reticle);
            var root = new GameObject("Reticle");
            var quad = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Object.DestroyImmediate(quad.GetComponent<Collider>());
            quad.name = "Ring";
            quad.transform.SetParent(root.transform, false);
            quad.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            quad.transform.localScale = Vector3.one * 0.16f;
            var renderer = quad.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = MaterialFactory.Unlit("Reticle", Color.white, texture);
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            return SaveAsPrefab(root, path);
        }

        public static ApiSettings ApiSettings() =>
            LoadOrCreate<ApiSettings>($"{ProjectPaths.Settings}/ApiSettings.asset");

        static Color Theme(uint rgb) => UI.Theme.Hex(rgb);

        static Texture2D Surface(string name, int size, System.Func<int, int, int, Color> pixel) =>
            AssetDatabase.LoadAssetAtPath<Texture2D>($"{ProjectPaths.Textures}/{name}.png") ?? TextureFactory.Surface(name, size, pixel);

        static Sprite LoadOr(string name, System.Func<Sprite> create) =>
            AssetDatabase.LoadAssetAtPath<Sprite>($"{ProjectPaths.Sprites}/{name}.png") ?? create();

        static T LoadOrCreate<T>(string path) where T : ScriptableObject
        {
            var asset = AssetDatabase.LoadAssetAtPath<T>(path);
            if (asset != null)
                return asset;
            asset = ScriptableObject.CreateInstance<T>();
            AssetDatabase.CreateAsset(asset, path);
            return asset;
        }

        static GameObject SaveAsPrefab(GameObject instance, string path)
        {
            var prefab = PrefabUtility.SaveAsPrefabAsset(instance, path);
            Object.DestroyImmediate(instance);
            return prefab;
        }
    }
}
