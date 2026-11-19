using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace FloorPlanViz.Editor
{
    /// <summary>Render quality for a small, close-up model: full resolution, MSAA, crisp soft shadows that also fall on the transparent shadow catcher.</summary>
    public static class RenderingSetup
    {
        [MenuItem("Floor Plan Viz/Configure Rendering")]
        public static void Configure()
        {
            foreach (var guid in AssetDatabase.FindAssets("t:UniversalRenderPipelineAsset", new[] { "Assets/Settings" }))
                ConfigureAsset(AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(AssetDatabase.GUIDToAssetPath(guid)));
            foreach (var guid in AssetDatabase.FindAssets("t:UniversalRendererData", new[] { "Assets/Settings" }))
            {
                var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(AssetDatabase.GUIDToAssetPath(guid));
                renderer.shadowTransparentReceive = true;
                EditorUtility.SetDirty(renderer);
            }

            GraphicsSettings.lightsUseLinearIntensity = true;
            GraphicsSettings.lightsUseColorTemperature = true;
            PlayerSettings.statusBarHidden = false;
            AssetDatabase.SaveAssets();
        }

        static void ConfigureAsset(UniversalRenderPipelineAsset asset)
        {
            var serialized = new SerializedObject(asset);
            serialized.FindProperty("m_MSAA").intValue = 4;
            serialized.FindProperty("m_RenderScale").floatValue = 1f;
            serialized.FindProperty("m_MainLightShadowsSupported").boolValue = true;
            serialized.FindProperty("m_MainLightShadowmapResolution").intValue = 2048;
            serialized.FindProperty("m_ShadowDistance").floatValue = 20f;
            serialized.FindProperty("m_ShadowCascadeCount").intValue = 2;
            serialized.FindProperty("m_Cascade2Split").floatValue = 0.1f;
            serialized.FindProperty("m_SoftShadowsSupported").boolValue = true;
            serialized.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(asset);
        }
    }
}
