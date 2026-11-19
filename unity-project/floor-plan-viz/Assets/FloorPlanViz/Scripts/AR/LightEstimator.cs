using UnityEngine;
using UnityEngine.XR.ARFoundation;

namespace FloorPlanViz.AR
{
    /// <summary>Matches the sun and ambient light to the brightness and colour temperature of the real room.</summary>
    [RequireComponent(typeof(Light))]
    public sealed class LightEstimator : MonoBehaviour
    {
        const float NeutralLumens = 1000f;
        const float MinFactor = 0.35f;
        const float MaxFactor = 1.4f;

        [SerializeField] ARCameraManager cameraManager;

        Light sun;
        float baseIntensity;
        Color baseSky;
        Color baseEquator;
        Color baseGround;

        void Awake()
        {
            sun = GetComponent<Light>();
            baseIntensity = sun.intensity;
            baseSky = RenderSettings.ambientSkyColor;
            baseEquator = RenderSettings.ambientEquatorColor;
            baseGround = RenderSettings.ambientGroundColor;
        }

        void OnEnable() => cameraManager.frameReceived += OnFrame;

        void OnDisable() => cameraManager.frameReceived -= OnFrame;

        void OnFrame(ARCameraFrameEventArgs frame)
        {
            var estimate = frame.lightEstimation;
            var factor = estimate.averageIntensityInLumens is { } lumens ? lumens / NeutralLumens
                : estimate.averageBrightness is { } brightness ? brightness * 2f
                : 1f;
            factor = Mathf.Clamp(factor, MinFactor, MaxFactor);

            sun.intensity = baseIntensity * factor;
            if (estimate.averageColorTemperature is { } kelvin)
                sun.colorTemperature = kelvin;

            RenderSettings.ambientSkyColor = baseSky * factor;
            RenderSettings.ambientEquatorColor = baseEquator * factor;
            RenderSettings.ambientGroundColor = baseGround * factor;
        }
    }
}
