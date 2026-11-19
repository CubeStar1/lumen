using FloorPlanViz.AR;
using FloorPlanViz.Debugging;
using FloorPlanViz.Model;
using FloorPlanViz.UI;
using Unity.XR.CoreUtils;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.Rendering;
using UnityEngine.UI;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

namespace FloorPlanViz.Editor
{
    /// <summary>Rebuilds the app's scenes from code so their setup is reproducible and reviewable.</summary>
    public static class SceneBuilder
    {
        [MenuItem("Floor Plan Viz/Rebuild Scenes")]
        public static void BuildAll()
        {
            AssetBuilder.BuildAll();
            RenderingSetup.Configure();
            BuildDebugScene();
            BuildMainScene();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ProjectPaths.MainScene, true) };
        }

        public static void BuildDebugScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            AddLighting();

            var camera = new GameObject("Camera", typeof(Camera), typeof(OrbitCamera));
            camera.tag = "MainCamera";
            var view = camera.GetComponent<Camera>();
            view.clearFlags = CameraClearFlags.SolidColor;
            view.backgroundColor = new Color(0.86f, 0.87f, 0.89f);

            var builder = AddBuilder(new GameObject("Builder"));
            var loader = new GameObject("Plan").AddComponent<DebugPlanLoader>();
            SerializedWiring.Set(loader, "builder", builder);
            SerializedWiring.Set(loader, "orbitCamera", camera.GetComponent<OrbitCamera>());
            SerializedWiring.Set(loader, "plan", AssetDatabase.LoadAssetAtPath<TextAsset>(ProjectPaths.SamplePlan));

            EditorSceneManager.SaveScene(scene, ProjectPaths.DebugScene);
        }

        public static void BuildMainScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var sun = AddLighting();

            EditorApplication.ExecuteMenuItem("GameObject/XR/XR Origin (Mobile AR)");
            if (Object.FindAnyObjectByType<ARSession>() == null)
                EditorApplication.ExecuteMenuItem("GameObject/XR/AR Session");
            var session = Object.FindAnyObjectByType<ARSession>();
            var origin = Object.FindAnyObjectByType<XROrigin>();
            var viewer = ConfigureCamera(origin.Camera);

            var estimation = sun.gameObject.AddComponent<LightEstimator>();
            SerializedWiring.Set(estimation, "cameraManager", origin.Camera.GetComponent<ARCameraManager>());

            var planes = GetOrAdd<ARPlaneManager>(origin.gameObject);
            planes.planePrefab = AssetBuilder.PlanePrefab();
            planes.requestedDetectionMode = PlaneDetectionMode.Horizontal;
            var raycasts = GetOrAdd<ARRaycastManager>(origin.gameObject);
            var anchors = GetOrAdd<ARAnchorManager>(origin.gameObject);
            var reticle = (GameObject)PrefabUtility.InstantiatePrefab(AssetBuilder.ReticlePrefab());

            var app = new GameObject("App");
            var builder = AddBuilder(app);
            var gestures = app.AddComponent<ModelGestures>();
            var viewMode = app.AddComponent<ViewModeController>();
            SerializedWiring.Set(viewMode, "viewer", viewer);
            SerializedWiring.Set(viewMode, "gestures", gestures);

            var placement = app.AddComponent<PlacementController>();
            SerializedWiring.Set(placement, "raycastManager", raycasts);
            SerializedWiring.Set(placement, "planeManager", planes);
            SerializedWiring.Set(placement, "anchorManager", anchors);
            SerializedWiring.Set(placement, "viewer", viewer);
            SerializedWiring.Set(placement, "reticle", reticle.transform);

            UiKit.Use(AssetBuilder.Ui());
            var (backdrop, pages, overlays) = AddCanvas();
            var library = LibraryBuilder.Build(pages);
            var detail = DetailBuilder.Build(pages);
            var hud = HudBuilder.Build(pages);
            SerializedWiring.Set(viewMode, "walker", AddWalker(origin.Camera, hud));
            var editSheet = OverlayBuilder.Edit(overlays);
            var settingsSheet = OverlayBuilder.Settings(overlays);
            var actionSheet = OverlayBuilder.Actions(overlays);
            var promptDialog = OverlayBuilder.Prompt(overlays);
            var processing = OverlayBuilder.Processing(overlays);
            var toast = OverlayBuilder.ToastBanner(overlays);

            var ar = app.AddComponent<ArExperience>();
            SerializedWiring.Set(ar, "session", session);
            SerializedWiring.Set(ar, "builder", builder);
            SerializedWiring.Set(ar, "placement", placement);
            SerializedWiring.Set(ar, "viewMode", viewMode);
            SerializedWiring.Set(ar, "hud", hud);

            var requests = app.AddComponent<RequestRunner>();
            SerializedWiring.Set(requests, "overlay", processing);
            SerializedWiring.Set(requests, "toast", toast);

            var flow = app.AddComponent<AppFlow>();
            SerializedWiring.Set(flow, "apiSettings", AssetBuilder.ApiSettings());
            SerializedWiring.Set(flow, "samplePlan", AssetDatabase.LoadAssetAtPath<TextAsset>(ProjectPaths.SamplePlan));
            SerializedWiring.Set(flow, "backdrop", backdrop);
            SerializedWiring.Set(flow, "requests", requests);
            SerializedWiring.Set(flow, "ar", ar);
            SerializedWiring.Set(flow, "library", library);
            SerializedWiring.Set(flow, "detail", detail);
            SerializedWiring.Set(flow, "hud", hud);
            SerializedWiring.Set(flow, "editSheet", editSheet);
            SerializedWiring.Set(flow, "settingsSheet", settingsSheet);
            SerializedWiring.Set(flow, "actionSheet", actionSheet);
            SerializedWiring.Set(flow, "promptDialog", promptDialog);
            SerializedWiring.Set(flow, "toast", toast);

            foreach (var hidden in new AppScreen[] { detail, hud, editSheet, settingsSheet, actionSheet, promptDialog, processing, toast })
                hidden.gameObject.SetActive(false);

            EditorSceneManager.SaveScene(scene, ProjectPaths.MainScene);
        }

        static Transform ConfigureCamera(Camera camera)
        {
            camera.tag = "MainCamera";
            camera.GetComponent<ARCameraManager>().requestedLightEstimation =
                UnityEngine.XR.ARFoundation.LightEstimation.AmbientIntensity | UnityEngine.XR.ARFoundation.LightEstimation.AmbientColor;
            var occlusion = GetOrAdd<AROcclusionManager>(camera.gameObject);
            occlusion.requestedHumanStencilMode = HumanSegmentationStencilMode.Fastest;
            occlusion.requestedHumanDepthMode = HumanSegmentationDepthMode.Fastest;
            occlusion.requestedEnvironmentDepthMode = EnvironmentDepthMode.Disabled;
            return camera.transform;
        }

        /// <summary>The first-person body and its camera, off until the walkthrough asks for game controls.</summary>
        static FirstPersonWalker AddWalker(Camera arCamera, ArHud hud)
        {
            var body = new GameObject("Walker", typeof(CharacterController));
            var eye = new GameObject("WalkCamera", typeof(Camera));
            eye.tag = "MainCamera";
            eye.transform.SetParent(body.transform, false);
            var view = eye.GetComponent<Camera>();
            view.clearFlags = CameraClearFlags.SolidColor;
            view.backgroundColor = new Color(0.74f, 0.83f, 0.93f);
            view.nearClipPlane = 0.05f;
            view.farClipPlane = 300f;
            view.fieldOfView = 70f;

            var walker = body.AddComponent<FirstPersonWalker>();
            SerializedWiring.Set(walker, "view", view);
            SerializedWiring.Set(walker, "arView", arCamera);
            SerializedWiring.Set(walker, "joystick", hud.GetComponentInChildren<VirtualJoystick>(true));
            SerializedWiring.Set(walker, "lookPad", hud.GetComponentInChildren<LookPad>(true));
            body.SetActive(false);
            return walker;
        }

        static FloorPlanBuilder AddBuilder(GameObject host)
        {
            var builder = host.AddComponent<FloorPlanBuilder>();
            SerializedWiring.Set(builder, "palette", AssetBuilder.Palette());
            SerializedWiring.Set(builder, "labelPrefab", AssetBuilder.LabelPrefab());
            return builder;
        }

        /// <summary>A warm key light with soft shadows and a cool sky / warm ground ambient, so wall faces read differently.</summary>
        static Light AddLighting()
        {
            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.85f;
            sun.shadowBias = 0.02f;
            sun.shadowNormalBias = 0.2f;
            sun.intensity = 1.25f;
            sun.useColorTemperature = true;
            sun.colorTemperature = 5600f;
            sun.transform.rotation = Quaternion.Euler(52f, -35f, 0f);

            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.78f, 0.82f, 0.9f);
            RenderSettings.ambientEquatorColor = new Color(0.66f, 0.66f, 0.66f);
            RenderSettings.ambientGroundColor = new Color(0.45f, 0.42f, 0.38f);
            RenderSettings.ambientIntensity = 1f;
            return sun;
        }

        static (GameObject backdrop, Transform pages, Transform overlays) AddCanvas()
        {
            var canvas = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster), typeof(DensityScaler));
            canvas.GetComponent<Canvas>().renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.GetComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ConstantPixelSize;

            new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule));

            var backdrop = UiKit.Stretch(UiKit.Node("Backdrop", canvas.transform));
            UiKit.Fill(backdrop, Theme.Background);
            var pages = UiKit.Stretch(UiKit.Node("Pages", canvas.transform));
            pages.gameObject.AddComponent<SafeAreaPanel>();
            var overlays = UiKit.Stretch(UiKit.Node("Overlays", canvas.transform));
            return (backdrop.gameObject, pages, overlays);
        }

        static T GetOrAdd<T>(GameObject host) where T : Component =>
            host.TryGetComponent<T>(out var component) ? component : host.AddComponent<T>();
    }
}
