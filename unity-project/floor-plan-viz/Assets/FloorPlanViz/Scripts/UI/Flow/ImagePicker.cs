using UnityEngine;

namespace FloorPlanViz.UI
{
    public static class ImagePicker
    {
        /// <summary>Lets the user pick a photo. Returns a readable texture, or null if nothing was picked.</summary>
        public static async Awaitable<Texture2D> PickAsync(int maxSize)
        {
            var completion = new AwaitableCompletionSource<string>();
            NativeGallery.GetImageFromGallery(path => completion.SetResult(path), "Choose a floor plan", "image/*");
            var path = await completion.Awaitable;

            return string.IsNullOrEmpty(path)
                ? null
                : NativeGallery.LoadImageAtPath(path, maxSize, markTextureNonReadable: false, generateMipmaps: false);
        }
    }
}
