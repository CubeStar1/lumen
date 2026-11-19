using System.IO;
using UnityEditor;
using UnityEditor.Callbacks;
#if UNITY_IOS
using UnityEditor.iOS.Xcode;
#endif

namespace FloorPlanViz.Editor
{
    /// <summary>Adds the Info.plist entries Unity has no Player setting for.</summary>
    static class IosPostProcess
    {
        [PostProcessBuild]
        static void OnPostProcessBuild(BuildTarget target, string buildPath)
        {
#if UNITY_IOS
            if (target != BuildTarget.iOS)
                return;

            var plistPath = Path.Combine(buildPath, "Info.plist");
            var plist = new PlistDocument();
            plist.ReadFromFile(plistPath);
            var root = plist.root;
            root.SetString("NSLocalNetworkUsageDescription", "Connects to the floor plan server on your local network.");
            root.SetString("NSPhotoLibraryUsageDescription", "Choose a floor plan image from your photos.");
            plist.WriteToFile(plistPath);
#endif
        }
    }
}
