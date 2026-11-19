using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace FloorPlanViz.Editor
{
    /// <summary>Creates or updates URP materials in the project's Materials folder.</summary>
    static class MaterialFactory
    {
        const string LitShader = "Universal Render Pipeline/Lit";
        const string UnlitShader = "Universal Render Pipeline/Unlit";

        public static Material Lit(string name, Color colour, float smoothness, Texture2D texture = null, float tileMetres = 1f, float metallic = 0f)
        {
            var material = Load(name, LitShader);
            material.SetColor("_BaseColor", colour);
            material.SetTexture("_BaseMap", texture);
            material.SetTextureScale("_BaseMap", Vector2.one / tileMetres);
            material.SetFloat("_Smoothness", smoothness);
            material.SetFloat("_Metallic", metallic);
            material.SetFloat("_EnvironmentReflections", 1f);
            MakeOpaque(material);
            return Save(material);
        }

        public static Material Glass(string name, Color colour, float smoothness)
        {
            var material = Load(name, LitShader);
            material.SetColor("_BaseColor", colour);
            material.SetFloat("_Smoothness", smoothness);
            material.SetFloat("_Metallic", 0f);
            MakeTransparent(material);
            return Save(material);
        }

        public static Material Unlit(string name, Color colour, Texture2D texture, float tiling = 1f)
        {
            var material = Load(name, UnlitShader);
            material.SetColor("_BaseColor", colour);
            material.SetTexture("_BaseMap", texture);
            material.SetTextureScale("_BaseMap", Vector2.one * tiling);
            MakeTransparent(material);
            return Save(material);
        }

        public static Material ShadowCatcher(string name, float strength)
        {
            var material = Load(name, "FloorPlanViz/Shadow Catcher");
            material.SetFloat("_ShadowStrength", strength);
            return Save(material);
        }

        static Material Load(string name, string shaderName)
        {
            var shader = Shader.Find(shaderName) ?? throw new System.InvalidOperationException($"Shader '{shaderName}' not found.");
            var path = $"{ProjectPaths.Materials}/{name}.mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, path);
            }
            material.shader = shader;
            return material;
        }

        static void MakeOpaque(Material material)
        {
            material.SetFloat("_Surface", 0f);
            material.SetOverrideTag("RenderType", "Opaque");
            material.SetFloat("_SrcBlend", (float)BlendMode.One);
            material.SetFloat("_DstBlend", (float)BlendMode.Zero);
            material.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
            material.SetFloat("_DstBlendAlpha", (float)BlendMode.Zero);
            material.SetFloat("_ZWrite", 1f);
            material.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
            material.renderQueue = (int)RenderQueue.Geometry;
            material.SetShaderPassEnabled("ShadowCaster", true);
        }

        static void MakeTransparent(Material material)
        {
            material.SetFloat("_Surface", 1f);
            material.SetFloat("_Blend", 0f);
            material.SetOverrideTag("RenderType", "Transparent");
            material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            material.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
            material.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
            material.SetFloat("_ZWrite", 0f);
            material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            material.renderQueue = (int)RenderQueue.Transparent;
            material.SetShaderPassEnabled("ShadowCaster", false);
        }

        static Material Save(Material material)
        {
            EditorUtility.SetDirty(material);
            return material;
        }
    }
}
