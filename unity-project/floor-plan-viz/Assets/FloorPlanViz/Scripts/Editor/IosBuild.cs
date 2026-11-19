using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;

namespace FloorPlanViz.Editor
{
    /// <summary>Exports the Xcode project that is then signed and run from a Mac.</summary>
    public static class IosBuild
    {
        public const string OutputPath = "Builds/iOS";

        [MenuItem("Floor Plan Viz/Build iOS Xcode Project")]
        public static void Build()
        {
            PlatformSetup.Configure();
            EditorSceneManager.SaveOpenScenes();
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ProjectPaths.MainScene },
                locationPathName = OutputPath,
                target = BuildTarget.iOS,
                targetGroup = BuildTargetGroup.iOS,
            });

            if (report.summary.result != BuildResult.Succeeded)
                throw new BuildFailedException($"iOS build {report.summary.result} with {report.summary.totalErrors} errors.");
            if (!Directory.Exists(Path.Combine(OutputPath, "Unity-iPhone.xcodeproj")))
                throw new BuildFailedException("No Xcode project was written. Restart the Editor if iOS Build Support was just installed.");
        }
    }
}
