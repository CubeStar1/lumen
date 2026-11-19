using System.Linq;
using UnityEditor;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEngine;
using UnityEngine.Rendering.Universal;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.Management;

namespace FloorPlanViz.Editor
{
    /// <summary>Configures player and XR settings for the iOS build and in-Editor XR Simulation.</summary>
    public static class PlatformSetup
    {
        const string BundleId = "com.thecubestar.floorplanviz";
        const string MinimumIosVersion = "15.0";
        const string ArKitLoader = "UnityEngine.XR.ARKit.ARKitLoader";
        const string SimulationLoader = "UnityEngine.XR.Simulation.SimulationLoader";
        const string GeneralSettingsPath = "Assets/XR/XRGeneralSettingsPerBuildTarget.asset";

        [MenuItem("Floor Plan Viz/Configure iOS")]
        public static void Configure()
        {
            ConfigurePlayer();
            EnableLoader(BuildTargetGroup.iOS, ArKitLoader);
            EnableLoader(BuildTargetGroup.Standalone, SimulationLoader);
            foreach (var guid in AssetDatabase.FindAssets("t:UniversalRendererData", new[] { "Assets/Settings" }))
                AddCameraBackground(AssetDatabase.LoadAssetAtPath<UniversalRendererData>(AssetDatabase.GUIDToAssetPath(guid)));
            AssetDatabase.SaveAssets();
        }

        /// <summary>URP only draws the AR camera feed when the renderer has this feature.</summary>
        static void AddCameraBackground(UniversalRendererData renderer)
        {
            if (renderer.rendererFeatures.Any(f => f is ARBackgroundRendererFeature))
                return;

            var feature = ScriptableObject.CreateInstance<ARBackgroundRendererFeature>();
            feature.name = nameof(ARBackgroundRendererFeature);
            feature.hideFlags = HideFlags.HideInHierarchy;
            AssetDatabase.AddObjectToAsset(feature, renderer);
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(feature, out _, out long localId);

            var serialized = new SerializedObject(renderer);
            var features = serialized.FindProperty("m_RendererFeatures");
            var map = serialized.FindProperty("m_RendererFeatureMap");
            features.InsertArrayElementAtIndex(features.arraySize);
            features.GetArrayElementAtIndex(features.arraySize - 1).objectReferenceValue = feature;
            map.InsertArrayElementAtIndex(map.arraySize);
            map.GetArrayElementAtIndex(map.arraySize - 1).longValue = localId;
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }

        static void ConfigurePlayer()
        {
            PlayerSettings.companyName = "thecubestar";
            PlayerSettings.productName = "Floor Plan AR";
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.iOS, BundleId);
            PlayerSettings.iOS.targetDevice = iOSTargetDevice.iPhoneAndiPad;
            PlayerSettings.iOS.targetOSVersionString = MinimumIosVersion;
            PlayerSettings.iOS.cameraUsageDescription = "The camera shows your floor plan model in augmented reality.";
            PlayerSettings.insecureHttpOption = InsecureHttpOption.AlwaysAllowed;
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToPortrait = true;
            PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true;
            PlayerSettings.allowedAutorotateToLandscapeRight = true;
        }

        static void EnableLoader(BuildTargetGroup group, string loaderType)
        {
            var perTarget = GeneralSettings();
            if (!perTarget.HasManagerSettingsForBuildTarget(group))
                perTarget.CreateDefaultManagerSettingsForBuildTarget(group);

            var settings = perTarget.SettingsForBuildTarget(group);
            settings.InitManagerOnStart = true;
            XRPackageMetadataStore.AssignLoader(settings.Manager, loaderType, group);
            EditorUtility.SetDirty(perTarget);
        }

        static XRGeneralSettingsPerBuildTarget GeneralSettings()
        {
            if (EditorBuildSettings.TryGetConfigObject(XRGeneralSettings.settingsKey, out XRGeneralSettingsPerBuildTarget existing) && existing != null)
                return existing;

            var created = ScriptableObject.CreateInstance<XRGeneralSettingsPerBuildTarget>();
            AssetDatabase.CreateAsset(created, GeneralSettingsPath);
            EditorBuildSettings.AddConfigObject(XRGeneralSettings.settingsKey, created, true);
            return created;
        }
    }
}
