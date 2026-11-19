using System;
using System.Collections.Generic;
using System.Linq;
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
                : Load(path, maxSize);
        }

        /// <summary>Lets the user pick several photos, or one where the gallery can't pick more. Returns the readable textures.</summary>
        public static async Awaitable<List<Texture2D>> PickManyAsync(int maxSize, string title)
        {
            if (!NativeGallery.CanSelectMultipleFilesFromGallery())
            {
                var single = await PickAsync(maxSize);
                return single == null ? new List<Texture2D>() : new List<Texture2D> { single };
            }

            var completion = new AwaitableCompletionSource<string[]>();
            NativeGallery.GetImagesFromGallery(paths => completion.SetResult(paths), title, "image/*");
            var paths = await completion.Awaitable ?? Array.Empty<string>();
            return paths.Select(path => Load(path, maxSize)).Where(texture => texture != null).ToList();
        }

        static Texture2D Load(string path, int maxSize) =>
            NativeGallery.LoadImageAtPath(path, maxSize, markTextureNonReadable: false, generateMipmaps: false);
    }
}
